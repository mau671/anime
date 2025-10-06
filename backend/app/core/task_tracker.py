"""Utility for tracking task execution history."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import Any

from structlog.stdlib import BoundLogger

from app.core.utils import utc_now
from app.db.models import TaskHistoryDocument
from app.db.repositories import TaskHistoryRepository


class TaskTracker:
    """Context manager for tracking task execution."""

    def __init__(
        self,
        repo: TaskHistoryRepository,
        task_type: str,
        trigger: str,
        logger: BoundLogger,
        anilist_id: int | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> None:
        self.repo = repo
        self.task_id = f"{task_type}_{uuid.uuid4().hex[:12]}"
        self.task_type = task_type
        self.trigger = trigger
        self.anilist_id = anilist_id
        self.parameters = parameters or {}
        self.logger = logger
        self.document: dict | None = None

        # Statistics
        self.items_processed = 0
        self.items_succeeded = 0
        self.items_failed = 0
        self.result: dict[str, Any] | None = None

    async def start(self) -> str:
        """Start tracking the task."""
        doc = TaskHistoryDocument(
            task_id=self.task_id,
            task_type=self.task_type,
            status="running",
            trigger=self.trigger,
            anilist_id=self.anilist_id,
            parameters=self.parameters,
        )

        self.document = await self.repo.create(doc)
        self.logger.info(
            "task_started",
            task_id=self.task_id,
            task_type=self.task_type,
            trigger=self.trigger,
        )
        return self.task_id

    async def complete(self, result: dict[str, Any] | None = None) -> None:
        """Mark the task as completed."""
        await self.repo.update(
            self.task_id,
            {
                "status": "completed",
                "completed_at": utc_now(),
                "result": result or {},
                "items_processed": self.items_processed,
                "items_succeeded": self.items_succeeded,
                "items_failed": self.items_failed,
            },
        )
        self.logger.info(
            "task_completed",
            task_id=self.task_id,
            items_processed=self.items_processed,
            items_succeeded=self.items_succeeded,
            items_failed=self.items_failed,
        )

    async def fail(self, error: str) -> None:
        """Mark the task as failed."""
        await self.repo.update(
            self.task_id,
            {
                "status": "failed",
                "completed_at": utc_now(),
                "error": error,
                "items_processed": self.items_processed,
                "items_succeeded": self.items_succeeded,
                "items_failed": self.items_failed,
            },
        )
        self.logger.error(
            "task_failed",
            task_id=self.task_id,
            error=error,
        )

    def increment_processed(self, count: int = 1) -> None:
        """Increment items processed counter."""
        self.items_processed += count

    def increment_succeeded(self, count: int = 1) -> None:
        """Increment items succeeded counter."""
        self.items_succeeded += count

    def increment_failed(self, count: int = 1) -> None:
        """Increment items failed counter."""
        self.items_failed += count

    def set_result(self, result: dict[str, Any]) -> None:
        """Attach result payload to be stored on completion."""
        self.result = result


@asynccontextmanager
async def track_task(
    repo: TaskHistoryRepository,
    task_type: str,
    trigger: str,
    logger: BoundLogger,
    anilist_id: int | None = None,
    parameters: dict[str, Any] | None = None,
):
    """Context manager for tracking a task."""
    tracker = TaskTracker(repo, task_type, trigger, logger, anilist_id, parameters)

    try:
        await tracker.start()
        yield tracker
        await tracker.complete(tracker.result or {})
    except Exception as exc:
        await tracker.fail(str(exc))
        raise
