from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.utils import utc_now


class MongoModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    def to_mongo(self) -> dict[str, Any]:
        payload = self.model_dump(by_alias=True, exclude_none=True)
        payload["updated_at"] = payload.get("updated_at") or utc_now()
        return payload


class AnimeDocument(MongoModel):
    anilist_id: int = Field(alias="anilist_id")
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
    source: str = "nyaa"
    title: str
    link: str
    magnet: str | None = None
    infohash: str | None = None
    published_at: datetime | None = None
    saved_at: datetime = Field(default_factory=utc_now)

    def to_mongo(self) -> dict[str, Any]:
        payload = super().to_mongo()
        payload.setdefault("saved_at", utc_now())
        return payload
