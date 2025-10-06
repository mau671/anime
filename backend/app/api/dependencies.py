"""FastAPI dependencies for API endpoints."""

from __future__ import annotations

from fastapi import HTTPException, Request

from app.core.bootstrap import ServiceContainer
from app.scheduler.service import SchedulerService


def get_container(request: Request) -> ServiceContainer:
    """Get the service container from app state."""
    container: ServiceContainer | None = getattr(request.app.state, "container", None)
    if container is None:
        raise HTTPException(status_code=503, detail="Service container not ready")
    return container


def get_scheduler(request: Request) -> SchedulerService:
    scheduler: SchedulerService | None = getattr(request.app.state, "scheduler", None)
    if scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not available")
    return scheduler
