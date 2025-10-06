from __future__ import annotations

import asyncio

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any, Awaitable

from bson import ObjectId
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.schemas import (
    AnimeEnvelope,
    AnimeResource,
    ScanNyaaResponse,
    SettingsEnvelope,
    SettingsResource,
    SettingsUpdatePayload,
    SyncAnilistRequest,
    SyncAnilistResponse,
    TaskStatusResponse,
    TMDBMetadata,
    TVDBMetadata,
    TorrentSeenRecord,
)
from app.core.bootstrap import ServiceContainer, build_container
from app.core.config import get_settings
from app.core.utils import ensure_directory, sanitize_save_path, utc_now
from app.db.models import AnimeSettingsDocument
from app.scheduler.operations import scan_nyaa_sources, sync_anilist_catalog
from app.scheduler.service import SchedulerService


def _normalize_document(data: dict[str, Any] | None) -> dict[str, Any] | None:
    if data is None:
        return None

    def _convert(value: Any) -> Any:
        if isinstance(value, ObjectId):
            return str(value)
        if isinstance(value, dict):
            return {k: _convert(v) for k, v in value.items() if k != "_id"}
        if isinstance(value, list):
            return [_convert(item) for item in value]
        return value

    normalized: dict[str, Any] = {k: _convert(v) for k, v in data.items() if k != "_id"}
    if "_id" in data:
        normalized.setdefault("id", str(data["_id"]))
    return normalized


def _ensure_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    return [str(value)]


def _build_anime_resource(anime_entry: dict[str, Any]) -> AnimeResource:
    normalized = _normalize_document(anime_entry) or {}
    normalized["genres"] = _ensure_str_list(normalized.get("genres"))
    normalized["synonyms"] = _ensure_str_list(normalized.get("synonyms"))
    title = normalized.get("title")
    if title is not None and not isinstance(title, dict):
        normalized["title"] = {"romaji": str(title)}
    return AnimeResource.model_validate(normalized)


def _coerce_optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


async def _fetch_external_metadata(
    container: ServiceContainer,
    *,
    tvdb_id: int | None,
    tvdb_season: int | None,
    tmdb_id: int | None,
    tmdb_season: int | None,
    anilist_id: int | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    calls: list[tuple[str, Awaitable[dict[str, Any] | None]]] = []
    if tvdb_id is not None and container.tvdb_client.enabled:
        calls.append(("tvdb", container.tvdb_client.get_metadata(tvdb_id, season=tvdb_season)))
    if tmdb_id is not None and container.tmdb_client.enabled:
        calls.append(("tmdb", container.tmdb_client.get_metadata(tmdb_id, season=tmdb_season)))

    tvdb_meta: dict[str, Any] | None = None
    tmdb_meta: dict[str, Any] | None = None

    if not calls:
        return tvdb_meta, tmdb_meta

    results = await asyncio.gather(*(task for _, task in calls), return_exceptions=True)
    for index, result in enumerate(results):
        label = calls[index][0]
        if isinstance(result, Exception):
            container.logger.warning(
                "external_metadata_error",
                provider=label,
                anilist_id=anilist_id,
                error=str(result),
            )
            continue
        if label == "tvdb":
            tvdb_meta = result
        elif label == "tmdb":
            tmdb_meta = result

    return tvdb_meta, tmdb_meta


async def _build_settings_envelope(
    container: ServiceContainer,
    settings_entry: dict[str, Any],
    anime_entry: dict[str, Any] | None,
) -> SettingsEnvelope:
    normalized_settings = _normalize_document(settings_entry) or {}
    anilist_id = normalized_settings.get("anilist_id")
    is_global = anilist_id == 0
    tvdb_id = _coerce_optional_int(normalized_settings.get("tvdb_id"))
    tvdb_season = _coerce_optional_int(normalized_settings.get("tvdb_season"))
    tmdb_id = _coerce_optional_int(normalized_settings.get("tmdb_id"))
    tmdb_season = _coerce_optional_int(normalized_settings.get("tmdb_season"))

    if "tvdb_id" in normalized_settings or tvdb_id is not None:
        normalized_settings["tvdb_id"] = tvdb_id
    if "tvdb_season" in normalized_settings or tvdb_season is not None:
        normalized_settings["tvdb_season"] = tvdb_season
    if "tmdb_id" in normalized_settings or tmdb_id is not None:
        normalized_settings["tmdb_id"] = tmdb_id
    if "tmdb_season" in normalized_settings or tmdb_season is not None:
        normalized_settings["tmdb_season"] = tmdb_season
    normalized_settings["includes"] = _ensure_str_list(normalized_settings.get("includes"))
    normalized_settings["excludes"] = _ensure_str_list(normalized_settings.get("excludes"))
    if is_global:
        normalized_settings["enabled"] = False
        tvdb_meta = None
        tmdb_meta = None
    else:
        tvdb_meta, tmdb_meta = await _fetch_external_metadata(
            container,
            tvdb_id=tvdb_id,
            tvdb_season=tvdb_season,
            tmdb_id=tmdb_id,
            tmdb_season=tmdb_season,
            anilist_id=anilist_id,
        )
    settings_model = SettingsResource.model_validate(normalized_settings)
    anime_model = None if is_global else (_build_anime_resource(anime_entry) if anime_entry else None)
    tvdb_model = TVDBMetadata.model_validate(tvdb_meta) if tvdb_meta else None
    tmdb_model = TMDBMetadata.model_validate(tmdb_meta) if tmdb_meta else None
    return SettingsEnvelope(
        settings=settings_model,
        anime=anime_model,
        tvdb_metadata=tvdb_model,
        tmdb_metadata=tmdb_model,
    )


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with build_container() as container:
        scheduler = SchedulerService(
            scheduler=container.scheduler,
            settings=container.settings,
            logger=container.logger.bind(component="scheduler"),
            anime_repo=container.anime_repo,
            settings_repo=container.settings_repo,
            torrent_repo=container.torrent_repo,
            anilist_client=container.anilist_client,
            nyaa_client=container.nyaa_client,
            downloader=container.downloader,
            tvdb_client=container.tvdb_client,
            tmdb_client=container.tmdb_client,
        )
        await scheduler.start()
        app.state.container = container
        app.state.scheduler = scheduler
        try:
            yield
        finally:
            await scheduler.shutdown()
            app.state.container = None
            app.state.scheduler = None


app = FastAPI(title="Anime Torrent Monitor", version="1.1.0", lifespan=_lifespan)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_container(request: Request) -> ServiceContainer:
    container: ServiceContainer | None = getattr(request.app.state, "container", None)
    if container is None:
        raise HTTPException(status_code=503, detail="Service container not ready")
    return container


def get_scheduler(request: Request) -> SchedulerService:
    scheduler: SchedulerService | None = getattr(request.app.state, "scheduler", None)
    if scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not available")
    return scheduler


@app.get("/health", response_model=TaskStatusResponse)
async def health(container: ServiceContainer = Depends(get_container)) -> TaskStatusResponse:
    await container.anime_repo.ensure_indexes()
    await container.settings_repo.ensure_indexes()
    await container.torrent_repo.ensure_indexes()
    await container.mongo_client.admin.command("ping")
    return TaskStatusResponse(status="ok", detail="Service healthy")


@app.get("/animes", response_model=list[AnimeEnvelope])
async def list_animes(
    limit: int = Query(50, ge=1, le=500),
    container: ServiceContainer = Depends(get_container),
) -> list[AnimeEnvelope]:
    items = await container.anime_repo.all()
    limited = items[:limit]
    return [AnimeEnvelope(anime=_build_anime_resource(item)) for item in limited]


@app.get("/settings", response_model=list[SettingsEnvelope])
async def list_settings(container: ServiceContainer = Depends(get_container)) -> list[SettingsEnvelope]:
    entries = await container.settings_repo.list_all()
    anime_ids = [entry["anilist_id"] for entry in entries if entry.get("anilist_id") not in (None, 0)]
    anime_map = await container.anime_repo.get_by_ids(anime_ids) if anime_ids else {}
    envelopes: list[SettingsEnvelope] = []
    for entry in entries:
        anime_entry = None if entry.get("anilist_id") == 0 else anime_map.get(entry["anilist_id"])
        envelope = await _build_settings_envelope(container, entry, anime_entry)
        envelopes.append(envelope)
    return envelopes


@app.get("/settings/{anilist_id}/downloads", response_model=list[TorrentSeenRecord])
async def list_download_history(
    anilist_id: int,
    limit: int = Query(50, ge=1, le=200),
    container: ServiceContainer = Depends(get_container),
) -> list[TorrentSeenRecord]:
    entries = await container.torrent_repo.list_for_anilist(anilist_id, limit=limit)
    result: list[TorrentSeenRecord] = []
    for entry in entries:
        normalized = _normalize_document(entry) or {}
        normalized.setdefault("anilist_id", anilist_id)
        result.append(TorrentSeenRecord.model_validate(normalized))
    return result


@app.get("/settings/{anilist_id}", response_model=SettingsEnvelope)
async def get_settings_by_id(
    anilist_id: int,
    container: ServiceContainer = Depends(get_container),
) -> SettingsEnvelope:
    entry = await container.settings_repo.get(anilist_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Settings not found")
    anime = None
    if anilist_id != 0:
        anime = (await container.anime_repo.get_by_ids([anilist_id])).get(anilist_id)
    return await _build_settings_envelope(container, entry, anime)


@app.put("/settings/{anilist_id}", response_model=SettingsEnvelope)
async def update_settings(
    anilist_id: int,
    payload: SettingsUpdatePayload,
    container: ServiceContainer = Depends(get_container),
) -> SettingsEnvelope:
    is_global = anilist_id == 0
    existing_entry = await container.settings_repo.get(anilist_id)
    data = payload.model_dump(exclude_unset=True)

    defaults: dict[str, Any] = {}
    if not is_global and existing_entry is None:
        global_defaults = await container.settings_repo.get(0)
        if global_defaults:
            defaults = {
                key: deepcopy(value)
                for key, value in global_defaults.items()
                if key
                not in {
                    "_id",
                    "id",
                    "anilist_id",
                    "created_at",
                    "updated_at",
                    "save_path",
                }
            }

    base = deepcopy(existing_entry) if existing_entry else {}
    for field in ("_id", "id", "created_at", "updated_at"):
        base.pop(field, None)

    merged: dict[str, Any] = {**defaults, **base, **data}
    merged["anilist_id"] = anilist_id

    includes = merged.get("includes")
    if includes is not None:
        merged["includes"] = [item.strip() for item in includes if item and item.strip()]
    else:
        merged.setdefault("includes", [])

    excludes = merged.get("excludes")
    if excludes is not None:
        merged["excludes"] = [item.strip() for item in excludes if item and item.strip()]
    else:
        merged.setdefault("excludes", [])

    if merged.get("preferred_resolution"):
        merged["preferred_resolution"] = str(merged["preferred_resolution"]).upper()

    template_value = merged.get("save_path_template")
    if template_value is not None:
        stripped = template_value.strip()
        merged["save_path_template"] = stripped or None

    resolved_path = merged.get("save_path")
    if resolved_path:
        if is_global:
            merged["save_path"] = resolved_path.strip() or None
        else:
            sanitized = sanitize_save_path(Path(resolved_path))
            ensure_directory(
                sanitized,
                create=container.settings.create_missing_save_dirs,
                logger=container.logger,
            )
            merged["save_path"] = str(sanitized)

    for field in ("tvdb_id", "tvdb_season", "tmdb_id", "tmdb_season"):
        if field in merged:
            merged[field] = _coerce_optional_int(merged[field])

    if is_global:
        merged["enabled"] = False

    document = AnimeSettingsDocument(**merged)
    updated = await container.settings_repo.upsert(document)
    anime = None
    if not is_global:
        anime = (await container.anime_repo.get_by_ids([anilist_id])).get(anilist_id)
    return await _build_settings_envelope(container, updated, anime)


@app.delete("/settings/{anilist_id}", response_model=TaskStatusResponse)
async def delete_settings(
    anilist_id: int,
    container: ServiceContainer = Depends(get_container),
) -> TaskStatusResponse:
    deleted = await container.settings_repo.delete(anilist_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Settings not found")
    return TaskStatusResponse(status="ok", detail=f"Removed settings for {anilist_id}")


@app.post("/tasks/init-db", response_model=TaskStatusResponse)
async def init_db(container: ServiceContainer = Depends(get_container)) -> TaskStatusResponse:
    await container.anime_repo.ensure_indexes()
    await container.settings_repo.ensure_indexes()
    await container.torrent_repo.ensure_indexes()
    return TaskStatusResponse(status="ok", detail="Indexes ensured")


@app.post("/tasks/sync-anilist", response_model=SyncAnilistResponse)
async def sync_anilist(
    payload: SyncAnilistRequest,
    container: ServiceContainer = Depends(get_container),
) -> SyncAnilistResponse:
    count = await sync_anilist_catalog(
        settings=container.settings,
        client=container.anilist_client,
        repository=container.anime_repo,
        logger=container.logger,
        season=payload.season,
        season_year=payload.season_year,
    )
    season_used = (payload.season or container.settings.api.season).upper()
    year_used = payload.season_year or container.settings.api.season_year or utc_now().year
    return SyncAnilistResponse(
        status="completed",
        count=count,
        season=season_used,
        season_year=year_used,
    )


@app.post("/tasks/scan-nyaa", response_model=ScanNyaaResponse)
async def trigger_scan(
    container: ServiceContainer = Depends(get_container),
) -> ScanNyaaResponse:
    await scan_nyaa_sources(
        settings=container.settings,
        anime_repo=container.anime_repo,
        settings_repo=container.settings_repo,
        torrent_repo=container.torrent_repo,
        nyaa_client=container.nyaa_client,
        downloader=container.downloader,
        tvdb_client=container.tvdb_client,
        tmdb_client=container.tmdb_client,
        logger=container.logger,
    )
    return ScanNyaaResponse(status="completed")


@app.post("/scheduler/reload", response_model=TaskStatusResponse)
async def reload_scheduler(scheduler: SchedulerService = Depends(get_scheduler)) -> TaskStatusResponse:
    await scheduler.shutdown()
    await scheduler.start()
    return TaskStatusResponse(status="ok", detail="Scheduler restarted")
