"""Tests for application configuration API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.db.models import AppConfigDocument
from app.db.repositories import AppConfigRepository


@pytest.mark.asyncio
async def test_get_app_config_empty(client: AsyncClient, config_repo: AppConfigRepository):
    """Test getting app config when none exists."""
    response = await client.get("/config/")
    assert response.status_code == 200

    data = response.json()
    assert data["qbittorrent_enabled"] is False
    assert data["auto_add_to_qbittorrent"] is False
    assert data["qbittorrent_category"] == "anime"


@pytest.mark.asyncio
async def test_update_app_config(client: AsyncClient, config_repo: AppConfigRepository):
    """Test updating application configuration."""
    payload = {
        "tvdb_api_key": "test_tvdb_key",
        "tmdb_api_key": "test_tmdb_key",
        "qbittorrent_enabled": True,
        "qbittorrent_url": "http://localhost:8080",
        "qbittorrent_username": "admin",
        "qbittorrent_password": "secret",
        "qbittorrent_category": "anime",
        "path_mappings": [{"from": "/storage/data/torrents", "to": "/data/torrents"}],
        "auto_add_to_qbittorrent": True,
    }

    response = await client.put("/config/", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["tvdb_api_key"] == "test_tvdb_key"
    assert data["tmdb_api_key"] == "test_tmdb_key"
    assert data["qbittorrent_enabled"] is True
    assert data["qbittorrent_url"] == "http://localhost:8080"
    assert data["qbittorrent_username"] == "admin"
    assert data["qbittorrent_password"] == "***"  # Should be masked
    assert data["auto_add_to_qbittorrent"] is True
    assert len(data["path_mappings"]) == 1

    # Verify it was saved in DB
    saved = await config_repo.get()
    assert saved is not None
    assert saved["qbittorrent_enabled"] is True


@pytest.mark.asyncio
async def test_update_partial_app_config(client: AsyncClient, config_repo: AppConfigRepository):
    """Test partial update of application configuration."""
    # First create a config
    await config_repo.upsert(
        AppConfigDocument(
            qbittorrent_enabled=False,
            qbittorrent_url="http://old-url:8080",
        )
    )

    # Update only some fields
    payload = {
        "qbittorrent_enabled": True,
        "auto_add_to_qbittorrent": True,
    }

    response = await client.put("/config/", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["qbittorrent_enabled"] is True
    assert data["auto_add_to_qbittorrent"] is True
    # Old values should be preserved
    assert data["qbittorrent_url"] == "http://old-url:8080"


@pytest.mark.asyncio
async def test_get_app_config_after_update(client: AsyncClient, config_repo: AppConfigRepository):
    """Test getting app config after updating it."""
    # Create config
    await config_repo.upsert(
        AppConfigDocument(
            tvdb_api_key="my_tvdb_key",
            qbittorrent_enabled=True,
            qbittorrent_password="secret123",
        )
    )

    response = await client.get("/config/")
    assert response.status_code == 200

    data = response.json()
    assert data["tvdb_api_key"] == "my_tvdb_key"
    assert data["qbittorrent_enabled"] is True
    assert data["qbittorrent_password"] == "***"  # Should be masked


@pytest.mark.asyncio
async def test_path_mappings_conversion(client: AsyncClient):
    """Test path mappings are correctly converted."""
    payload = {
        "path_mappings": [
            {"from": "/storage/data", "to": "/data"},
            {"from": "/storage/media", "to": "/media"},
        ]
    }

    response = await client.put("/config/", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert len(data["path_mappings"]) == 2
    assert data["path_mappings"][0]["from"] == "/storage/data"
    assert data["path_mappings"][0]["to"] == "/data"
    assert data["path_mappings"][1]["from"] == "/storage/media"
    assert data["path_mappings"][1]["to"] == "/media"


@pytest.mark.asyncio
async def test_default_settings_fields_persist(
    client: AsyncClient, config_repo: AppConfigRepository
):
    payload = {
        "default_save_path": "/storage/data/torrents",
        "default_save_path_template": "/storage/data/torrents/{anime.title.romaji}",
        "default_search_query_template": "{anime.title.romaji} {currentYear}",
        "default_preferred_resolution": "1080P",
        "default_preferred_subgroup": "SubsPlease",
        "default_auto_query_from_synonyms": True,
    }

    response = await client.put("/config/", json=payload)
    assert response.status_code == 200

    data = response.json()
    for key, value in payload.items():
        assert data[key] == value

    saved = await config_repo.get()
    assert saved is not None
    for key, value in payload.items():
        assert saved[key] == value
