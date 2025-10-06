"""API endpoints for application configuration."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_container
from app.api.schemas import AppConfigPayload, AppConfigResponse, PathMapping
from app.core.bootstrap import ServiceContainer
from app.db.models import AppConfigDocument

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/", response_model=AppConfigResponse)
async def get_app_config(
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> AppConfigResponse:
    """Get the current application configuration."""
    config = await container.config_repo.get()

    if not config:
        # Return default configuration if none exists
        return AppConfigResponse()

    # Mask password for security
    if config.get("qbittorrent_password"):
        config["qbittorrent_password"] = "***"

    # Convert path_mappings to PathMapping objects
    path_mappings = []
    for mapping in config.get("path_mappings", []):
        path_mappings.append(
            PathMapping(from_path=mapping.get("from", ""), to_path=mapping.get("to", ""))
        )
    config["path_mappings"] = path_mappings

    return AppConfigResponse(**config)


@router.put("/", response_model=AppConfigResponse)
async def update_app_config(
    payload: AppConfigPayload,
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> AppConfigResponse:
    """Update the application configuration."""
    # Get existing config or create new one
    existing = await container.config_repo.get()

    if existing:
        config_doc = AppConfigDocument(**existing)
    else:
        config_doc = AppConfigDocument()

    # Update fields from payload (only non-None values)
    update_data = payload.model_dump(exclude_none=True)

    # Convert path_mappings to dict format
    if "path_mappings" in update_data and update_data["path_mappings"] is not None:
        path_mappings_dicts = []
        for mapping in update_data["path_mappings"]:
            if isinstance(mapping, PathMapping):
                path_mappings_dicts.append(
                    {
                        "from": mapping.from_path,
                        "to": mapping.to_path,
                    }
                )
            elif isinstance(mapping, dict):
                path_mappings_dicts.append(
                    {
                        "from": mapping.get("from") or mapping.get("from_path", ""),
                        "to": mapping.get("to") or mapping.get("to_path", ""),
                    }
                )
        update_data["path_mappings"] = path_mappings_dicts

    # Update config document
    for key, value in update_data.items():
        setattr(config_doc, key, value)

    # Save to database
    updated = await container.config_repo.upsert(config_doc)

    # Mask password for response
    if updated.get("qbittorrent_password"):
        updated["qbittorrent_password"] = "***"

    # Convert path_mappings to PathMapping objects for response
    path_mappings = []
    for mapping in updated.get("path_mappings", []):
        path_mappings.append(
            PathMapping(from_path=mapping.get("from", ""), to_path=mapping.get("to", ""))
        )
    updated["path_mappings"] = path_mappings

    container.logger.info("app_config_updated", fields=list(update_data.keys()))

    return AppConfigResponse(**updated)


@router.post("/test-qbittorrent")
async def test_qbittorrent_connection(
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> dict[str, str]:
    """Test the qBittorrent connection with current settings."""
    from app.qbittorrent.client import QBittorrentClient

    config = await container.config_repo.get()
    if not config:
        raise HTTPException(status_code=400, detail="No configuration found")

    if not config.get("qbittorrent_enabled"):
        raise HTTPException(status_code=400, detail="qBittorrent is not enabled")

    url = config.get("qbittorrent_url")
    if not url:
        raise HTTPException(status_code=400, detail="qBittorrent URL not configured")

    client = QBittorrentClient(
        url=url,
        username=config.get("qbittorrent_username"),
        password=config.get("qbittorrent_password"),
        category=config.get("qbittorrent_category", "anime"),
        logger=container.logger.bind(component="qbittorrent"),
    )

    try:
        version = await client.get_version()
        if version:
            return {"status": "ok", "version": version}
        else:
            return {"status": "error", "message": "Could not get version"}
    except Exception as exc:
        container.logger.error("qbittorrent_test_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Connection failed: {exc}") from exc
    finally:
        await client.close()
