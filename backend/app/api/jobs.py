from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field

from app.api.dependencies import get_container
from app.api.schemas import (
    ExportQbittorrentJob,
    InitDbJob,
    JobExecutionResponse,
    JobTypeInfo,
    JobTypeListResponse,
    QBittorrentHistoryListResponse,
    QBittorrentHistoryRecord,
    ScanNyaaJob,
    ScanNyaaResponse,
    SyncAnilistJob,
    TaskHistoryFilters,
    TaskHistoryListResponse,
    TaskHistoryResource,
    TaskRunningListResponse,
    TaskStatisticsResponse,
    TaskStatusAggregate,
)
from app.core.bootstrap import ServiceContainer
from app.core.task_tracker import track_task
from app.core.utils import utc_now
from app.db.models import QBittorrentHistoryDocument
from app.scheduler.operations import scan_nyaa_sources, sync_anilist_catalog

router = APIRouter(prefix="/jobs", tags=["jobs"])


async def _ensure_qbittorrent_enabled(container: ServiceContainer) -> dict:
    config = await container.config_repo.get()
    if not config or not config.get("qbittorrent_enabled"):
        raise HTTPException(status_code=400, detail="qBittorrent integration disabled")
    return config


def _resolve_job_payload(
    request: ScanNyaaJob | SyncAnilistJob | InitDbJob | ExportQbittorrentJob,
) -> tuple[str, dict[str, Any]]:
    job = request
    if isinstance(job, SyncAnilistJob):
        payload = job.model_dump(exclude={"job_type"}, exclude_none=True)
    elif isinstance(job, ExportQbittorrentJob):
        payload = job.model_dump(exclude={"job_type"}, exclude_none=True)
    elif isinstance(job, ScanNyaaJob):
        payload = {}
    elif isinstance(job, InitDbJob):
        payload = {}
    else:
        payload = {}
    return job.job_type, payload


async def _run_scan_nyaa(container: ServiceContainer) -> dict[str, Any]:
    await scan_nyaa_sources(
        settings=container.settings,
        anime_repo=container.anime_repo,
        settings_repo=container.settings_repo,
        torrent_repo=container.torrent_repo,
        config_repo=container.config_repo,
        task_history_repo=container.task_history_repo,
        qbittorrent_history_repo=container.qbittorrent_history_repo,
        nyaa_client=container.nyaa_client,
        downloader=container.downloader,
        tvdb_client=container.tvdb_client,
        tmdb_client=container.tmdb_client,
        logger=container.logger,
        trigger="api",
    )
    return {"status": "completed"}


async def _run_sync_anilist(
    container: ServiceContainer,
    payload: dict[str, Any],
) -> dict[str, Any]:
    season = payload.get("season") if payload else None
    season_year = payload.get("season_year") if payload else None

    if season_year is not None:
        try:
            season_year = int(season_year)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="season_year must be an integer")

    count = await sync_anilist_catalog(
        settings=container.settings,
        client=container.anilist_client,
        repository=container.anime_repo,
        task_history_repo=container.task_history_repo,
        logger=container.logger,
        season=season,
        season_year=season_year,
        trigger="api",
    )

    season_used = (season or container.settings.api.season).upper()
    year_used = season_year or container.settings.api.season_year or utc_now().year

    return {
        "count": count,
        "season": season_used,
        "season_year": year_used,
    }


async def _run_init_db(container: ServiceContainer) -> dict[str, str]:
    await container.anime_repo.ensure_indexes()
    await container.settings_repo.ensure_indexes()
    await container.torrent_repo.ensure_indexes()
    await container.task_history_repo.ensure_indexes()
    await container.qbittorrent_history_repo.ensure_indexes()
    return {"detail": "Indexes ensured"}


async def _run_export_qbittorrent(
    container: ServiceContainer,
    payload: dict[str, Any],
) -> dict[str, Any]:
    from app.qbittorrent.client import QBittorrentClient
    from app.qbittorrent.path_mapper import PathMapper

    config = await _ensure_qbittorrent_enabled(container)

    limit_raw = payload.get("limit", 50)
    try:
        limit = int(limit_raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="limit must be a positive integer")
    if limit <= 0 or limit > 200:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 200")

    anilist_id_raw = payload.get("anilist_id")
    anilist_id = None
    if anilist_id_raw is not None:
        try:
            anilist_id = int(anilist_id_raw)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="anilist_id must be an integer")
        if anilist_id <= 0:
            raise HTTPException(status_code=400, detail="anilist_id must be positive")

    items_raw = payload.get("items")
    if items_raw is not None and not isinstance(items_raw, list):
        raise HTTPException(status_code=400, detail="items must be a list")
    items: list[str] = [str(item) for item in items_raw] if items_raw else []

    torrents = await container.torrent_repo.list_pending_for_export(
        limit=limit,
        anilist_id=anilist_id,
        items=items,
    )
    if not torrents:
        return {"exported": 0, "skipped": 0, "failed": 0}

    qbit_client = QBittorrentClient(
        url=config.get("qbittorrent_url", ""),
        username=config.get("qbittorrent_username"),
        password=config.get("qbittorrent_password"),
        category=config.get("qbittorrent_category", "anime"),
        logger=container.logger.bind(component="qbittorrent-export"),
    )
    path_mapper = PathMapper(config.get("path_mappings", []))

    exported = skipped = failed = 0

    try:
        for entry in torrents:
            torrent_path = entry.get("torrent_path")
            if not torrent_path:
                skipped += 1
                continue

            backend_path = entry.get("save_path") or torrent_path
            mapped_save_path = path_mapper.to_qbittorrent(backend_path)

            added = await qbit_client.add_torrent(
                Path(torrent_path),
                Path(mapped_save_path),
            )
            if not added:
                failed += 1
                continue

            await container.qbittorrent_history_repo.record(
                QBittorrentHistoryDocument(
                    anilist_id=entry.get("anilist_id", 0),
                    title=entry.get("title") or Path(torrent_path).name,
                    torrent_path=str(Path(torrent_path).resolve()),
                    save_path=str(Path(mapped_save_path).resolve()),
                    category=config.get("qbittorrent_category", "anime"),
                    infohash=entry.get("infohash"),
                )
            )

            await container.torrent_repo.mark_exported(
                document_id=entry.get("_id"),
                exported=True,
                exported_at=utc_now(),
            )
            exported += 1
    finally:
        await qbit_client.close()

    return {
        "exported": exported,
        "skipped": skipped,
        "failed": failed,
    }


@router.post("/run", response_model=JobExecutionResponse)
async def run_job(
    request: Annotated[
        ScanNyaaJob | SyncAnilistJob | InitDbJob | ExportQbittorrentJob,
        Field(discriminator="job_type"),
    ],
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> JobExecutionResponse:
    job_type, payload = _resolve_job_payload(request)

    async with track_task(
        repo=container.task_history_repo,
        task_type=job_type,
        trigger="api",
        logger=container.logger,
    ) as tracker:
        if job_type == "scan_nyaa":
            result = await _run_scan_nyaa(container)
        elif job_type == "sync_anilist":
            result = await _run_sync_anilist(container, payload)
        elif job_type == "init_db":
            result = await _run_init_db(container)
        elif job_type == "export_qbittorrent":
            result = await _run_export_qbittorrent(container, payload)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown job type: {job_type}")

        tracker.set_result(result)

    return JobExecutionResponse(status="completed", task_id=tracker.task_id, result=result)


@router.get("/history", response_model=TaskHistoryListResponse)
async def list_job_history(
    container: Annotated[ServiceContainer, Depends(get_container)],
    limit: int = Query(50, ge=1, le=500),
    job_type: str | None = Query(None, description="Filter by job type"),
    status: str | None = Query(None, description="Filter by status"),
    anilist_id: int | None = Query(None, description="Filter by anime ID"),
) -> TaskHistoryListResponse:
    tasks = await container.task_history_repo.list_recent(
        limit=limit,
        task_type=job_type,
        status=status,
        anilist_id=anilist_id,
    )
    for task in tasks:
        if "_id" in task:
            task["id"] = str(task.pop("_id"))
    return TaskHistoryListResponse(
        tasks=[TaskHistoryResource(**task) for task in tasks],
        count=len(tasks),
        limit=limit,
        filters=TaskHistoryFilters(
            task_type=job_type,
            status=status,
            anilist_id=anilist_id,
        ),
    )


@router.get("/history/running", response_model=TaskRunningListResponse)
async def list_running_jobs(
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> TaskRunningListResponse:
    tasks = await container.task_history_repo.get_running_tasks()
    for task in tasks:
        if "_id" in task:
            task["id"] = str(task.pop("_id"))
    return TaskRunningListResponse(
        tasks=[TaskHistoryResource(**task) for task in tasks],
        count=len(tasks),
    )


@router.get("/history/{task_id}", response_model=TaskHistoryResource)
async def get_job(
    task_id: str,
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> TaskHistoryResource:
    task = await container.task_history_repo.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Job not found")
    if "_id" in task:
        task["id"] = str(task.pop("_id"))
    return TaskHistoryResource(**task)


@router.get("/history/statistics/summary", response_model=TaskStatisticsResponse)
async def get_job_statistics(
    container: Annotated[ServiceContainer, Depends(get_container)],
    job_type: str | None = Query(None),
    period: Literal["24h", "7d", "30d", "all"] = Query("24h"),
) -> TaskStatisticsResponse:
    since = None
    if period == "24h":
        since = datetime.utcnow() - timedelta(hours=24)
    elif period == "7d":
        since = datetime.utcnow() - timedelta(days=7)
    elif period == "30d":
        since = datetime.utcnow() - timedelta(days=30)
    stats = await container.task_history_repo.get_statistics(
        task_type=job_type,
        since=since,
    )
    aggregates: list[TaskStatusAggregate] = []
    for status_key, payload in stats.items():
        aggregates.append(
            TaskStatusAggregate(
                status=status_key,
                count=payload.get("count", 0),
                total_processed=payload.get("total_processed", 0),
                total_succeeded=payload.get("total_succeeded", 0),
                total_failed=payload.get("total_failed", 0),
            )
        )
    return TaskStatisticsResponse(
        period=period,
        task_type=job_type,
        statistics=aggregates,
    )


@router.get("/types", response_model=JobTypeListResponse)
async def list_job_types() -> JobTypeListResponse:
    return JobTypeListResponse(
        job_types=[
            JobTypeInfo(
                type="scan_nyaa",
                description="Scan tracked anime against Nyaa and download new torrents.",
                trigger_types=["scheduled", "manual", "api"],
            ),
            JobTypeInfo(
                type="sync_anilist",
                description="Refresh anime catalogue from AniList for a given season/year.",
                trigger_types=["scheduled", "manual", "api"],
            ),
            JobTypeInfo(
                type="init_db",
                description="Ensure MongoDB indexes exist for all collections.",
                trigger_types=["manual", "api"],
            ),
            JobTypeInfo(
                type="export_qbittorrent",
                description="Send downloaded torrents to qBittorrent using configured mappings.",
                trigger_types=["manual", "api"],
            ),
        ]
    )


@router.get("/history/qbittorrent/{anilist_id}", response_model=QBittorrentHistoryListResponse)
async def list_qbittorrent_history(
    anilist_id: int,
    container: Annotated[ServiceContainer, Depends(get_container)],
    limit: int = Query(50, ge=1, le=200),
) -> QBittorrentHistoryListResponse:
    records = await container.qbittorrent_history_repo.list_by_anilist(anilist_id, limit=limit)
    for record in records:
        if "_id" in record:
            record["id"] = str(record.pop("_id"))
    return QBittorrentHistoryListResponse(
        anilist_id=anilist_id,
        count=len(records),
        records=[QBittorrentHistoryRecord(**record) for record in records],
        limit=limit,
    )
