from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from structlog.stdlib import BoundLogger

from app.anilist.client import AniListClient
from app.anilist.models import Anime
from app.core.config import ServiceSettings
from app.core.task_tracker import track_task
from app.core.template import TemplateContext, build_base_context, render_template
from app.core.utils import ensure_directory, sanitize_save_path, utc_now
from app.db.models import AnimeDocument, QBittorrentHistoryDocument, TorrentSeenDocument
from app.db.repositories import (
    AnimeRepository,
    AnimeSettingsRepository,
    AppConfigRepository,
    QBittorrentHistoryRepository,
    TaskHistoryRepository,
    TorrentSeenRepository,
)
from app.downloader.torrent_downloader import TorrentDownloader
from app.metrics.registry import (
    ANILIST_UPSERTED,
    NYAA_ITEMS_FOUND,
    QB_TORRENTS_ADDED,
    QB_TORRENTS_FAILED,
    TORRENTS_DOWNLOADED,
    TORRENTS_ERRORS,
)
from app.scraper.filters import NyaaFilterInput, matches_filters
from app.scraper.nyaa_client import NyaaClient
from app.tmdb.client import TMDBClient
from app.tvdb.client import TVDBClient


def _anime_to_document(anime: Anime) -> AnimeDocument:
    return AnimeDocument(
        anilist_id=anime.anilist_id,
        title=anime.title.model_dump(),
        format=anime.format,
        season=anime.season,
        season_year=anime.season_year,
        status=anime.status,
        genres=anime.genres,
        synonyms=anime.synonyms,
        description=anime.description,
        average_score=anime.average_score,
        popularity=anime.popularity,
        cover_image=anime.cover_image,
        site_url=anime.site_url,
        updated_at=anime.updated_at,
    )


async def sync_anilist_catalog(
    settings: ServiceSettings,
    client: AniListClient,
    repository: AnimeRepository,
    task_history_repo: TaskHistoryRepository,
    logger: BoundLogger,
    season: str | None = None,
    season_year: int | None = None,
    trigger: str = "scheduled",
) -> int:
    season_value = (season or settings.api.season).upper()
    year_value = season_year or settings.api.season_year or utc_now().year
    async with track_task(
        repo=task_history_repo,
        task_type="sync_anilist",
        trigger=trigger,
        logger=logger,
        parameters={"season": season_value, "season_year": year_value},
    ) as tracker:
        try:
            anime_list = await client.fetch_releasing_anime(season_value, year_value)
            documents = (_anime_to_document(anime) for anime in anime_list)
            count = await repository.upsert_many(documents)

            tracker.increment_processed(len(anime_list))
            tracker.increment_succeeded(count)
            tracker.set_result(
                {
                    "count": count,
                    "season": season_value,
                    "season_year": year_value,
                }
            )

            ANILIST_UPSERTED.inc(count)
            logger.info(
                "anilist_sync_success",
                count=count,
                season=season_value,
                season_year=year_value,
            )
            return count
        except Exception:
            tracker.increment_failed()
            raise


def _build_search_query(setting: dict, anime: dict | None) -> str | None:
    query = setting.get("search_query")
    if query:
        return query
    if setting.get("auto_query_from_synonyms") and anime:
        titles: list[str] = []
        title_dict: dict | None = anime.get("title")
        if title_dict:
            titles.extend(
                [title_dict.get("romaji"), title_dict.get("english"), title_dict.get("native")]
            )
        titles.extend(anime.get("synonyms", []))
        filtered = [value for value in titles if value]
        if filtered:
            return " ".join(dict.fromkeys(filtered))
    return None


async def _build_template_values(
    entry: dict[str, Any],
    anime: dict[str, Any] | None,
    tvdb_client: TVDBClient,
    tmdb_client: TMDBClient,
    logger: BoundLogger,
) -> TemplateContext:
    """Build template context for save path rendering."""
    context: dict[str, Any] = build_base_context()

    # Add anime data with convenient aliases
    if anime:
        anime_context = dict(anime)
        # Add camelCase aliases for consistency
        if "anilist_id" in anime_context:
            anime_context["anilistId"] = anime_context["anilist_id"]
        if "season_year" in anime_context:
            anime_context["seasonYear"] = anime_context["season_year"]
        context["anime"] = anime_context

    # Fetch TVDB metadata if configured
    tvdb_id = entry.get("tvdb_id")
    tvdb_season = entry.get("tvdb_season")
    if tvdb_id is not None and tvdb_client.enabled:
        try:
            tvdb_meta = await tvdb_client.get_metadata(tvdb_id, season=tvdb_season)
            if tvdb_meta:
                # Format season number with zero padding for templates
                tvdb_meta_enhanced = dict(tvdb_meta)
                season_num = tvdb_meta_enhanced.get("season")
                if season_num is not None:
                    # Format with zero padding (01, 02, 10, etc.)
                    tvdb_meta_enhanced["seasonNumber"] = f"{season_num:02d}"
                context["tvdb"] = tvdb_meta_enhanced
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "tvdb_metadata_fetch_failed",
                anilist_id=entry.get("anilist_id"),
                tvdb_id=tvdb_id,
                error=str(exc),
            )

    # Fetch TMDB metadata if configured
    tmdb_id = entry.get("tmdb_id")
    tmdb_season = entry.get("tmdb_season")
    if tmdb_id is not None and tmdb_client.enabled:
        try:
            tmdb_meta = await tmdb_client.get_metadata(tmdb_id, season=tmdb_season)
            if tmdb_meta:
                # Format season number with zero padding for templates
                tmdb_meta_enhanced = dict(tmdb_meta)
                season_num = tmdb_meta_enhanced.get("season")
                if season_num is not None:
                    # Format with zero padding (01, 02, 10, etc.)
                    tmdb_meta_enhanced["seasonNumber"] = f"{season_num:02d}"
                context["tmdb"] = tmdb_meta_enhanced
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "tmdb_metadata_fetch_failed",
                anilist_id=entry.get("anilist_id"),
                tmdb_id=tmdb_id,
                error=str(exc),
            )

    return context


async def scan_nyaa_sources(
    settings: ServiceSettings,
    anime_repo: AnimeRepository,
    settings_repo: AnimeSettingsRepository,
    torrent_repo: TorrentSeenRepository,
    config_repo: AppConfigRepository,
    task_history_repo: TaskHistoryRepository,
    qbittorrent_history_repo: QBittorrentHistoryRepository,
    nyaa_client: NyaaClient,
    downloader: TorrentDownloader,
    tvdb_client: TVDBClient,
    tmdb_client: TMDBClient,
    logger: BoundLogger,
    trigger: str = "scheduled",
) -> None:
    async with track_task(
        repo=task_history_repo,
        task_type="scan_nyaa",
        trigger=trigger,
        logger=logger,
    ) as tracker:
        enabled_settings = await settings_repo.list_enabled()
        if not enabled_settings:
            logger.info("nyaa_scan_skip", reason="no_enabled_settings")
            tracker.set_result({"reason": "no_enabled_settings"})
            return

        # Load app configuration for qBittorrent integration
        app_config = await config_repo.get()
        qbit_enabled = (
            app_config
            and app_config.get("qbittorrent_enabled", False)
            and app_config.get("auto_add_to_qbittorrent", False)
        )
        qbit_client = None
        path_mapper = None

        if qbit_enabled:
            from app.qbittorrent.client import QBittorrentClient
            from app.qbittorrent.path_mapper import PathMapper

            qbit_client = QBittorrentClient(
                url=app_config.get("qbittorrent_url", ""),
                username=app_config.get("qbittorrent_username"),
                password=app_config.get("qbittorrent_password"),
                category=app_config.get("qbittorrent_category", "anime"),
                logger=logger.bind(component="qbittorrent"),
            )
            path_mapper = PathMapper(app_config.get("path_mappings", []))
            logger.info("qbittorrent_integration_enabled", url=app_config.get("qbittorrent_url"))

        anime_ids = [entry["anilist_id"] for entry in enabled_settings]
        anime_map = await anime_repo.get_by_ids(anime_ids)

        total_downloaded = 0
        total_failed = 0

        for entry in enabled_settings:
            anilist_id = entry["anilist_id"]
            anime = anime_map.get(anilist_id)
            query = _build_search_query(entry, anime)
            if not query:
                logger.warning("nyaa_scan_no_query", anilist_id=anilist_id)
                continue

            tracker.increment_processed()

            template_context = await _build_template_values(
                entry, anime, tvdb_client, tmdb_client, logger
            )

            save_path_raw = entry.get("save_path")
            save_path_template = entry.get("save_path_template")
            resolved_save_path: Path | None = None

            if save_path_template:
                rendered = render_template(save_path_template, template_context)
                if not rendered:
                    logger.warning(
                        "nyaa_save_path_template_empty",
                        anilist_id=anilist_id,
                        template=save_path_template,
                    )
                    continue
                resolved_save_path = sanitize_save_path(Path(rendered))
            elif save_path_raw:
                resolved_save_path = sanitize_save_path(Path(save_path_raw))
            else:
                logger.warning("nyaa_scan_missing_save_path", anilist_id=anilist_id)
                continue

            save_path = resolved_save_path
            try:
                ensure_directory(save_path, create=settings.create_missing_save_dirs, logger=logger)
            except ValueError as exc:
                logger.error("nyaa_invalid_save_path", anilist_id=anilist_id, error=str(exc))
                total_failed += 1
                tracker.increment_failed()
                continue

            try:
                items = await nyaa_client.fetch(query)
            except Exception as exc:  # noqa: BLE001
                logger.error("nyaa_fetch_error", anilist_id=anilist_id, error=str(exc))
                total_failed += 1
                tracker.increment_failed()
                continue

            if not items:
                logger.info("nyaa_no_items", anilist_id=anilist_id, query=query)
                continue

            NYAA_ITEMS_FOUND.labels(anilist_id=str(anilist_id)).inc(len(items))

            filters = NyaaFilterInput(
                includes=entry.get("includes") or [],
                excludes=entry.get("excludes") or [],
                preferred_resolution=entry.get("preferred_resolution"),
                preferred_subgroup=entry.get("preferred_subgroup"),
            )

            for item in items:
                if not matches_filters(item, filters):
                    logger.info(
                        "nyaa_item_skipped_filters", anilist_id=anilist_id, title=item.title
                    )
                    continue

                if await torrent_repo.exists(anilist_id, item.infohash, str(item.link)):
                    logger.info("nyaa_item_already_seen", anilist_id=anilist_id, title=item.title)
                    continue

                try:
                    filepath = await downloader.download(
                        str(item.link), item.title, item.infohash, save_path
                    )
                except Exception as exc:  # noqa: BLE001
                    TORRENTS_ERRORS.labels(anilist_id=str(anilist_id)).inc()
                    logger.error(
                        "nyaa_download_failed",
                        anilist_id=anilist_id,
                        title=item.title,
                        error=str(exc),
                    )
                    total_failed += 1
                    tracker.increment_failed()
                    continue

                TORRENTS_DOWNLOADED.labels(anilist_id=str(anilist_id)).inc()
                logger.info("nyaa_torrent_saved", anilist_id=anilist_id, path=str(filepath))
                total_downloaded += 1
                tracker.increment_succeeded()

                # Determine if this torrent should be auto-added to qBittorrent
                should_auto_add = qbit_enabled and qbit_client and path_mapper

                if should_auto_add:
                    try:
                        torrent_template = app_config.get("qbittorrent_torrent_template")
                        save_template = app_config.get("qbittorrent_save_template")

                        torrent_payload_path = (
                            Path(render_template(torrent_template, template_context))
                            if torrent_template
                            else filepath
                        )
                        save_payload_path = (
                            Path(render_template(save_template, template_context))
                            if save_template
                            else save_path
                        )

                        qbit_save_path_mapped = path_mapper.to_qbittorrent(save_payload_path)

                        added = await qbit_client.add_torrent(
                            torrent_payload_path,
                            qbit_save_path_mapped,
                        )
                        if added:
                            QB_TORRENTS_ADDED.inc()
                            await qbittorrent_history_repo.record(
                                QBittorrentHistoryDocument(
                                    anilist_id=anilist_id,
                                    title=item.title,
                                    torrent_path=str(torrent_payload_path),
                                    save_path=str(qbit_save_path_mapped),
                                    category=qbit_client.category,
                                    infohash=item.infohash,
                                )
                            )
                            logger.info(
                                "qbittorrent_torrent_added",
                                anilist_id=anilist_id,
                                title=item.title,
                                backend_path=str(save_path),
                                qbit_path=str(qbit_save_path_mapped),
                            )
                        else:
                            QB_TORRENTS_FAILED.inc()
                    except Exception as exc:  # noqa: BLE001
                        QB_TORRENTS_FAILED.inc()
                        logger.error(
                            "qbittorrent_add_failed",
                            anilist_id=anilist_id,
                            title=item.title,
                            error=str(exc),
                        )

                document = TorrentSeenDocument(
                    anilist_id=anilist_id,
                    title=item.title,
                    link=str(item.link),
                    magnet=str(item.magnet) if item.magnet else None,
                    infohash=item.infohash,
                    published_at=item.published_at,
                    save_path=str(save_path),
                    torrent_path=str(filepath),
                    exported_to_qbittorrent=should_auto_add,
                    exported_at=utc_now() if should_auto_add else None,
                )
                await torrent_repo.mark_seen(document)

        if qbit_client:
            await qbit_client.close()

        tracker.set_result(
            {
                "anime_tracked": len(enabled_settings),
                "downloaded": total_downloaded,
                "failures": total_failed,
            }
        )
