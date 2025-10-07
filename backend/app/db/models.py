from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core.utils import utc_now


class MongoModel(BaseModel):
    def to_mongo_dict(self) -> dict:
        payload = self.model_dump(by_alias=True, exclude_none=True)
        payload["updated_at"] = payload.get("updated_at") or utc_now()
        return payload


class AnimeDocument(MongoModel):
    anilist_id: int
    title: dict[str, str | None]
    format: str | None = None
    season: str | None = None
    season_year: int | None = None
    status: str | None = None
    genres: list[str] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)
    description: str | None = None
    average_score: int | None = None
    popularity: int | None = None
    cover_image: str | None = None
    site_url: str | None = None
    updated_at: datetime | None = None


class AnimeSettingsDocument(MongoModel):
    anilist_id: int
    enabled: bool = False
    save_path: str | None = None
    save_path_template: str | None = None
    search_query: str | None = None
    includes: list[str] = Field(default_factory=list)
    excludes: list[str] = Field(default_factory=list)
    preferred_resolution: str | None = None
    preferred_subgroup: str | None = None
    auto_query_from_synonyms: bool = False
    tvdb_id: int | None = None
    tvdb_season: int | None = None
    tmdb_id: int | None = None
    tmdb_season: int | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime | None = None


class TorrentSeenDocument(MongoModel):
    anilist_id: int
    title: str
    link: str
    magnet: str | None = None
    infohash: str
    published_at: datetime | None = None
    seen_at: datetime = Field(default_factory=utc_now)
    save_path: str | None = None
    torrent_path: str | None = None
    exported_to_qbittorrent: bool = False
    exported_at: datetime | None = None


class AppConfigDocument(MongoModel):
    """
    Application-wide configuration settings.
    Stored in MongoDB with a single document (config_key="app_config").
    """

    config_key: str = Field(default="app_config")  # Always "app_config" for singleton

    # API Keys
    tvdb_api_key: str | None = None
    tmdb_api_key: str | None = None

    # qBittorrent settings
    qbittorrent_enabled: bool = False
    qbittorrent_url: str | None = None
    qbittorrent_username: str | None = None
    qbittorrent_password: str | None = None
    qbittorrent_category: str = "anime"
    qbittorrent_torrent_template: str | None = None
    qbittorrent_save_template: str | None = None

    # Path mapping (backend path -> qBittorrent path)
    path_mappings: list[dict[str, str]] = Field(default_factory=list)
    # Example: [{"from": "/storage/data/torrents", "to": "/data/torrents"}]

    # Default anime settings
    default_save_path: str | None = None
    default_save_path_template: str | None = None
    default_search_query_template: str | None = None
    default_preferred_resolution: str | None = None
    default_preferred_subgroup: str | None = None
    default_auto_query_from_synonyms: bool = False

    # Other app settings
    auto_add_to_qbittorrent: bool = False

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime | None = None


class TaskHistoryDocument(MongoModel):
    """
    History of all tasks executed by the system.
    Tracks scans, syncs, and other operations.
    """

    task_id: str  # Unique identifier for the task
    task_type: str  # "scan_nyaa", "sync_anilist", "manual_scan", etc.
    status: str  # "pending", "running", "completed", "failed", "cancelled"
    trigger: str  # "manual", "scheduled", "api"

    # Timestamps
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None

    # Task details
    parameters: dict[str, Any] = Field(default_factory=dict)  # Input parameters
    result: dict[str, Any] = Field(default_factory=dict)  # Result data
    error: str | None = None  # Error message if failed

    # Statistics
    items_processed: int = 0
    items_succeeded: int = 0
    items_failed: int = 0

    # Related entities
    anilist_id: int | None = None  # For anime-specific tasks

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime | None = None


class QBittorrentHistoryDocument(MongoModel):
    """History of torrents exported to qBittorrent."""

    anilist_id: int
    title: str
    torrent_path: str
    save_path: str
    category: str | None = None
    infohash: str | None = None
    qbittorrent_response: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime | None = None
