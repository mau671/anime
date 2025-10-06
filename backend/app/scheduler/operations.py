from __future__ import annotations

import asyncio
from collections.abc import Mapping
from pathlib import Path

from structlog.stdlib import BoundLogger

from app.anilist.client import AniListClient
from app.anilist.models import Anime
from app.core.config import ServiceSettings
from app.core.utils import (
    ensure_directory,
    render_save_path_template,
    sanitize_save_path,
    utc_now,
)
from app.db.models import AnimeDocument, TorrentSeenDocument
from app.db.repositories import (
    AnimeRepository,
    AnimeSettingsRepository,
    TorrentSeenRepository,
)
from app.downloader.torrent_downloader import TorrentDownloader
from app.metrics.registry import (
    ANILIST_UPSERTED,
    NYAA_ITEMS_FOUND,
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
    logger: BoundLogger,
    season: str | None = None,
    season_year: int | None = None,
) -> int:
    season_value = (season or settings.api.season).upper()
    year_value = season_year or settings.api.season_year or utc_now().year
    anime_list = await client.fetch_releasing_anime(season_value, year_value)
    documents = (_anime_to_document(anime) for anime in anime_list)
    count = await repository.upsert_many(documents)
    ANILIST_UPSERTED.inc(count)
    logger.info("anilist_sync_success", count=count, season=season_value, season_year=year_value)
    return count


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


async def scan_nyaa_sources(
    settings: ServiceSettings,
    anime_repo: AnimeRepository,
    settings_repo: AnimeSettingsRepository,
    torrent_repo: TorrentSeenRepository,
    nyaa_client: NyaaClient,
    downloader: TorrentDownloader,
    logger: BoundLogger,
) -> None:
    enabled_settings = await settings_repo.list_enabled()
    if not enabled_settings:
        logger.info("nyaa_scan_skip", reason="no_enabled_settings")
        return

    anime_ids = [entry["anilist_id"] for entry in enabled_settings]
    anime_map = await anime_repo.get_by_ids(anime_ids)

    for entry in enabled_settings:
        anilist_id = entry["anilist_id"]
        anime = anime_map.get(anilist_id)
        query = _build_search_query(entry, anime)
        if not query:
            logger.warning("nyaa_scan_no_query", anilist_id=anilist_id)
            continue

        save_path_raw = entry.get("save_path")
        save_path_template = entry.get("save_path_template")
        resolved_save_path: Path | None = None

        if save_path_template:
            mapping = _build_template_values(settings, entry, anime)
            rendered = render_save_path_template(save_path_template, mapping)
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
            continue

        try:
            items = await nyaa_client.fetch(query)
        except Exception as exc:  # noqa: BLE001
            logger.error("nyaa_fetch_error", anilist_id=anilist_id, error=str(exc))
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
                logger.info("nyaa_item_skipped_filters", anilist_id=anilist_id, title=item.title)
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
                    "nyaa_download_failed", anilist_id=anilist_id, title=item.title, error=str(exc)
                )
                continue

            TORRENTS_DOWNLOADED.labels(anilist_id=str(anilist_id)).inc()
            logger.info("nyaa_torrent_saved", anilist_id=anilist_id, path=str(filepath))
            document = TorrentSeenDocument(
                anilist_id=anilist_id,
                title=item.title,
                link=str(item.link),
                magnet=str(item.magnet) if item.magnet else None,
                infohash=item.infohash,
                published_at=item.published_at,
            )
            await torrent_repo.mark_seen(document)
