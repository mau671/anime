"""API endpoints for task history and management."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_container
from app.core.bootstrap import ServiceContainer

router = APIRouter(prefix="/tasks/history", tags=["tasks"])


@router.get("/")
async def list_task_history(
    container: Annotated[ServiceContainer, Depends(get_container)],
    limit: int = Query(50, ge=1, le=500),
    task_type: str | None = Query(None, description="Filter by task type"),
    status: str | None = Query(None, description="Filter by status"),
    anilist_id: int | None = Query(None, description="Filter by anime ID"),
) -> dict:
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

    return {
        "tasks": tasks,
        "count": len(tasks),
        "limit": limit,
        "filters": {
            "task_type": task_type,
            "status": status,
            "anilist_id": anilist_id,
        },
    }


@router.get("/{task_id}")
async def get_task(
    task_id: str,
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> dict:
    """Get details of a specific task."""
    task = await container.task_history_repo.get_by_id(task_id)

    if not task:
        return {"error": "Task not found"}, 404

    if "_id" in task:
        task["id"] = str(task.pop("_id"))

    return task


@router.get("/running/list")
async def list_running_tasks(
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> dict:
    """Get all currently running tasks."""
    tasks = await container.task_history_repo.get_running_tasks()

    for task in tasks:
        if "_id" in task:
            task["id"] = str(task.pop("_id"))

    return {
        "tasks": tasks,
        "count": len(tasks),
    }


@router.get("/statistics/summary")
async def get_task_statistics(
    container: Annotated[ServiceContainer, Depends(get_container)],
    task_type: str | None = Query(None),
    period: Literal["24h", "7d", "30d", "all"] = Query("24h"),
) -> dict:
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

    return {
        "period": period,
        "task_type": task_type,
        "statistics": stats,
    }


@router.get("/types/list")
async def list_task_types(
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> dict:
    """Get all available task types."""
    return {
        "task_types": [
            {
                "type": "scan_nyaa",
                "description": "Scan Nyaa for new torrents",
                "trigger_types": ["scheduled", "manual", "api"],
            },
            {
                "type": "sync_anilist",
                "description": "Sync anime catalog from AniList",
                "trigger_types": ["scheduled", "manual", "api"],
            },
            {
                "type": "manual_scan",
                "description": "Manual scan triggered by user",
                "trigger_types": ["manual", "api"],
            },
        ]
    }
