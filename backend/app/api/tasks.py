"""API endpoints for task history and management."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_container
from app.api.schemas import (
    QBittorrentHistoryListResponse,
    QBittorrentHistoryRecord,
    TaskHistoryFilters,
    TaskHistoryListResponse,
    TaskHistoryResource,
    TaskRunningListResponse,
    TaskStatisticsResponse,
    TaskStatusAggregate,
    JobTypeInfo,
    JobTypeListResponse,
)
from app.core.bootstrap import ServiceContainer

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/history", response_model=TaskHistoryListResponse)
async def list_task_history(
    container: Annotated[ServiceContainer, Depends(get_container)],
    limit: int = Query(50, ge=1, le=500),
    task_type: str | None = Query(None, description="Filter by task type"),
    status: str | None = Query(None, description="Filter by status"),
    anilist_id: int | None = Query(None, description="Filter by anime ID"),
) -> TaskHistoryListResponse:
    """Get task execution history with optional filters."""
    tasks = await container.task_history_repo.list_recent(
        limit=limit,
        task_type=task_type,
        status=status,
        anilist_id=anilist_id,
    )

    # Normalize documents
    for task in tasks:
        if "_id" in task:
            task["id"] = str(task.pop("_id"))

    return TaskHistoryListResponse(
        tasks=[TaskHistoryResource(**task) for task in tasks],
        count=len(tasks),
        limit=limit,
        filters=TaskHistoryFilters(
            task_type=task_type,
            status=status,
            anilist_id=anilist_id,
        ),
    )


@router.get("/history/{task_id}", response_model=TaskHistoryResource)
async def get_task(
    task_id: str,
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> TaskHistoryResource:
    """Get details of a specific task."""
    task = await container.task_history_repo.get_by_id(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if "_id" in task:
        task["id"] = str(task.pop("_id"))

    return TaskHistoryResource(**task)


@router.get("/history/running", response_model=TaskRunningListResponse)
async def list_running_tasks(
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> TaskRunningListResponse:
    """Get all currently running tasks."""
    tasks = await container.task_history_repo.get_running_tasks()

    for task in tasks:
        if "_id" in task:
            task["id"] = str(task.pop("_id"))

    return TaskRunningListResponse(
        tasks=[TaskHistoryResource(**task) for task in tasks],
        count=len(tasks),
    )


@router.get("/history/statistics/summary", response_model=TaskStatisticsResponse)
async def get_task_statistics(
    container: Annotated[ServiceContainer, Depends(get_container)],
    task_type: str | None = Query(None),
    period: Literal["24h", "7d", "30d", "all"] = Query("24h"),
) -> TaskStatisticsResponse:
    """Get statistics about task execution."""
    since = None
    if period == "24h":
        since = datetime.utcnow() - timedelta(hours=24)
    elif period == "7d":
        since = datetime.utcnow() - timedelta(days=7)
    elif period == "30d":
        since = datetime.utcnow() - timedelta(days=30)

    stats = await container.task_history_repo.get_statistics(
        task_type=task_type,
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
        task_type=task_type,
        statistics=aggregates,
    )


@router.get("/types", response_model=JobTypeListResponse)
async def list_task_types(
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> JobTypeListResponse:
    """Get all available task types."""
    return JobTypeListResponse(
        job_types=[
            JobTypeInfo(
                type="scan_nyaa",
                description="Scan Nyaa for new torrents",
                trigger_types=["scheduled", "manual", "api"],
            ),
            JobTypeInfo(
                type="sync_anilist",
                description="Sync anime catalog from AniList",
                trigger_types=["scheduled", "manual", "api"],
            ),
            JobTypeInfo(
                type="manual_scan",
                description="Manual scan triggered by user",
                trigger_types=["manual", "api"],
            ),
            JobTypeInfo(
                type="qbittorrent_export",
                description="Torrents exported to qBittorrent",
                trigger_types=["scheduled", "manual"],
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
