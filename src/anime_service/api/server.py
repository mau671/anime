from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient

from anime_service.api.schemas import SettingsUpdatePayload
from anime_service.core.config import ServiceSettings, get_settings
from anime_service.db.models import AnimeSettingsDocument
from anime_service.db.mongo import create_motor_client, get_database
from anime_service.db.repositories import AnimeRepository, AnimeSettingsRepository

app = FastAPI(title="Anime Torrent Monitor", version="1.0.0")


async def get_repositories() -> tuple[
    AnimeRepository, AnimeSettingsRepository, AsyncIOMotorClient, ServiceSettings
]:
    settings = get_settings()
    client = create_motor_client(settings)
    db = get_database(client, settings)
    return AnimeRepository(db), AnimeSettingsRepository(db), client, settings


@app.get("/health")
async def health(
    repos: tuple[
        AnimeRepository, AnimeSettingsRepository, AsyncIOMotorClient, ServiceSettings
    ] = Depends(get_repositories),
) -> dict[str, str]:
    anime_repo, _settings_repo, client, _settings = repos
    try:
        await client.admin.command("ping")
    finally:
        client.close()
    return {"status": "ok"}


@app.get("/settings")
async def list_settings(
    repos: tuple[
        AnimeRepository, AnimeSettingsRepository, AsyncIOMotorClient, ServiceSettings
    ] = Depends(get_repositories),
) -> list[dict]:
    anime_repo, settings_repo, client, _settings = repos
    try:
        entries = await settings_repo.list_all()
        ids = [entry["anilist_id"] for entry in entries]
        anime_map = await anime_repo.get_by_ids(ids)
        response = []
        for entry in entries:
            metadata = anime_map.get(entry["anilist_id"], {})
            response.append({"settings": entry, "anime": metadata})
        return response
    finally:
        client.close()


@app.put("/settings/{anilist_id}")
async def update_settings(
    anilist_id: int,
    payload: SettingsUpdatePayload,
    repos: tuple[
        AnimeRepository, AnimeSettingsRepository, AsyncIOMotorClient, ServiceSettings
    ] = Depends(get_repositories),
) -> dict:
    _anime_repo, settings_repo, client, _settings = repos
    try:
        existing = await settings_repo.get(anilist_id) or {"anilist_id": anilist_id}
        merged = {**existing, **payload.model_dump(exclude_unset=True)}
        merged.pop("_id", None)
        document = AnimeSettingsDocument(**merged)
        updated = await settings_repo.upsert(document)
        return updated
    finally:
        client.close()


@app.get("/settings/{anilist_id}")
async def get_settings_by_id(
    anilist_id: int,
    repos: tuple[
        AnimeRepository, AnimeSettingsRepository, AsyncIOMotorClient, ServiceSettings
    ] = Depends(get_repositories),
) -> dict:
    _anime_repo, settings_repo, client, _settings = repos
    try:
        entry = await settings_repo.get(anilist_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Settings not found")
        return entry
    finally:
        client.close()


@app.delete("/settings/{anilist_id}")
async def delete_settings(
    anilist_id: int,
    repos: tuple[
        AnimeRepository, AnimeSettingsRepository, AsyncIOMotorClient, ServiceSettings
    ] = Depends(get_repositories),
) -> dict:
    _anime_repo, settings_repo, client, _settings = repos
    try:
        deleted = await settings_repo.delete(anilist_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Settings not found")
        return {"deleted": deleted}
    finally:
        client.close()
