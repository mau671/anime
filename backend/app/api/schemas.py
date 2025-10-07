from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, PositiveInt


class APIModel(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class SettingsUpdatePayload(BaseModel):
    enabled: bool | None = None
    save_path: str | None = None
    save_path_template: str | None = None
    search_query: str | None = None
    includes: list[str] | None = None
    excludes: list[str] | None = None
    preferred_resolution: Annotated[
        str | None, Field(pattern=r"^(?i)(480p|720p|1080p|2160p|4K)$", default=None)
    ] = None
    preferred_subgroup: str | None = None
    auto_query_from_synonyms: bool | None = None
    tvdb_id: PositiveInt | None = None
    tvdb_season: Annotated[int | None, Field(ge=0)] = None
    tmdb_id: PositiveInt | None = None
    tmdb_season: Annotated[int | None, Field(ge=0)] = None


class PathMapping(BaseModel):
    """Path mapping from backend to qBittorrent."""

    from_path: str = Field(alias="from")
    to_path: str = Field(alias="to")

    model_config = ConfigDict(populate_by_name=True)


class AppConfigPayload(BaseModel):
    """Payload for updating application configuration."""

    tvdb_api_key: str | None = None
    tmdb_api_key: str | None = None
    qbittorrent_enabled: bool | None = None
    qbittorrent_url: str | None = None
    qbittorrent_username: str | None = None
    qbittorrent_password: str | None = None
    qbittorrent_category: str | None = None
    path_mappings: list[PathMapping] | None = None
    auto_add_to_qbittorrent: bool | None = None
    qbittorrent_torrent_template: str | None = None
    qbittorrent_save_template: str | None = None
    default_save_path: str | None = None
    default_save_path_template: str | None = None
    default_search_query_template: str | None = None
    default_preferred_resolution: str | None = None
    default_preferred_subgroup: str | None = None
    default_auto_query_from_synonyms: bool | None = None


class AppConfigResponse(APIModel):
    """Response model for application configuration."""

    tvdb_api_key: str | None = None
    tmdb_api_key: str | None = None
    qbittorrent_enabled: bool = False
    qbittorrent_url: str | None = None
    qbittorrent_username: str | None = None
    qbittorrent_password: str | None = None  # Will be masked in actual response
    qbittorrent_category: str = "anime"
    path_mappings: list[PathMapping] = Field(default_factory=list)
    auto_add_to_qbittorrent: bool = False
    qbittorrent_torrent_template: str | None = None
    qbittorrent_save_template: str | None = None
    default_save_path: str | None = None
    default_save_path_template: str | None = None
    default_search_query_template: str | None = None
    default_preferred_resolution: str | None = None
    default_preferred_subgroup: str | None = None
    default_auto_query_from_synonyms: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TaskStatusResponse(BaseModel):
    status: Literal["ok", "completed", "queued", "failed"]
    detail: str | None = None


class SyncAnilistRequest(BaseModel):
    season: Literal["WINTER", "SPRING", "SUMMER", "FALL"] | None = None
    season_year: PositiveInt | None = None


class SyncAnilistResponse(TaskStatusResponse):
    count: int
    season: Literal["WINTER", "SPRING", "SUMMER", "FALL"]
    season_year: PositiveInt


class ScanNyaaResponse(TaskStatusResponse):
    status: Literal["completed", "queued", "ok"] = "completed"


class AnimeTitle(APIModel):
    romaji: str | None = None
    english: str | None = None
    native: str | None = None


class AnimeResource(APIModel):
    id: str | None = None
    anilist_id: int
    title: AnimeTitle | None = None
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


class SettingsResource(APIModel):
    id: str | None = None
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
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TVDBMetadata(APIModel):
    id: int
    name: str | None = None  # Translated name (if available) or original
    name_original: str | None = Field(default=None, alias="nameOriginal")  # Original name
    name_translated: str | None = Field(
        default=None, alias="nameTranslated"
    )  # Translated name (only if different)
    slug: str | None = None
    status: str | None = None
    overview: str | None = None
    first_aired: str | None = None
    year: int | None = None
    image: str | None = None
    network: str | None = None
    runtime: int | None = None
    season: int | None = None
    season_number: str | None = Field(
        default=None, alias="seasonNumber"
    )  # Zero-padded season (e.g., "01", "08")


class TMDBMetadata(APIModel):
    id: int
    type: Literal["movie", "tv"]
    title: str | None = None
    original_title: str | None = None
    name: str | None = None
    original_name: str | None = None
    release_date: str | None = None
    first_air_date: str | None = None
    year: int | None = None
    overview: str | None = None
    poster_path: str | None = None
    runtime: int | None = None
    genres: list[str] | None = None
    season: int | None = None
    season_number: str | None = Field(
        default=None, alias="seasonNumber"
    )  # Zero-padded season (e.g., "01", "08")
    season_name: str | None = None
    season_overview: str | None = None
    season_air_date: str | None = None
    episode_count: int | None = None


class SettingsEnvelope(APIModel):
    settings: SettingsResource
    anime: AnimeResource | None = None
    tvdb_metadata: TVDBMetadata | None = None
    tmdb_metadata: TMDBMetadata | None = None


class AnimeEnvelope(APIModel):
    anime: AnimeResource


class TorrentSeenRecord(APIModel):
    id: str | None = None
    anilist_id: int | None = None
    title: str
    link: str
    source: str | None = None
    magnet: str | None = None
    infohash: str | None = None
    saved_at: datetime | None = None
    published_at: datetime | None = None


class TaskHistoryResource(APIModel):
    id: str | None = None
    task_id: str
    task_type: str
    status: str
    trigger: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    items_processed: int = 0
    items_succeeded: int = 0
    items_failed: int = 0
    anilist_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TaskHistoryFilters(APIModel):
    task_type: str | None = None
    status: str | None = None
    anilist_id: int | None = None


class TaskHistoryListResponse(APIModel):
    tasks: list[TaskHistoryResource]
    count: int
    limit: int
    filters: TaskHistoryFilters


class TaskRunningListResponse(APIModel):
    tasks: list[TaskHistoryResource]
    count: int


class TaskStatusAggregate(APIModel):
    status: str
    count: int = 0
    total_processed: int = 0
    total_succeeded: int = 0
    total_failed: int = 0


class TaskStatisticsResponse(APIModel):
    period: Literal["24h", "7d", "30d", "all"]
    task_type: str | None = None
    statistics: list[TaskStatusAggregate]


class JobTypeInfo(APIModel):
    type: str
    description: str
    trigger_types: list[str]


class JobTypeListResponse(APIModel):
    job_types: list[JobTypeInfo]


class QBittorrentHistoryRecord(APIModel):
    id: str | None = None
    anilist_id: int
    title: str
    torrent_path: str
    save_path: str
    category: str | None = None
    infohash: str | None = None
    qbittorrent_response: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class QBittorrentHistoryListResponse(APIModel):
    anilist_id: int
    count: int
    records: list[QBittorrentHistoryRecord]
    limit: int


class JobTrigger(APIModel):
    id: str
    type: str
    next_run_time: datetime | None = None


class JobDetail(APIModel):
    id: str
    name: str | None = None
    func: str | None = None
    triggers: list[JobTrigger] = Field(default_factory=list)
    coalesce: bool | None = None
    misfire_grace_time: int | None = None
    max_instances: int | None = None


class JobListResponse(APIModel):
    jobs: list[JobDetail]
    count: int


class TorrentExportResult(APIModel):
    exported: int
    skipped: int
    failed: int


class TorrentExportResponse(TaskStatusResponse):
    result: TorrentExportResult


class ScanNyaaJob(APIModel):
    job_type: Literal["scan_nyaa"] = "scan_nyaa"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_type": "scan_nyaa",
            }
        }
    )


class SyncAnilistJob(APIModel):
    job_type: Literal["sync_anilist"] = "sync_anilist"
    season: Literal["WINTER", "SPRING", "SUMMER", "FALL"] | None = None
    season_year: PositiveInt | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_type": "sync_anilist",
                "season": "WINTER",
                "season_year": 2025,
            }
        }
    )


class InitDbJob(APIModel):
    job_type: Literal["init_db"] = "init_db"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_type": "init_db",
            }
        }
    )


class ExportQbittorrentJob(APIModel):
    job_type: Literal["export_qbittorrent"] = "export_qbittorrent"
    limit: PositiveInt = Field(default=50, le=200)
    anilist_id: PositiveInt | None = None
    items: list[str] = Field(
        default_factory=list,
        description="Explicit torrent paths or identifiers to export when available.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_type": "export_qbittorrent",
                "limit": 25,
                "anilist_id": 12345,
                "items": [
                    "/storage/downloads/anime/episode1.torrent",
                ],
            }
        }
    )


class JobExecutionResponse(TaskStatusResponse):
    task_id: str
    result: dict[str, Any] | None = None


