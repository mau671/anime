from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

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
