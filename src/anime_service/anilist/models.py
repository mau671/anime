from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AnimeTitle(BaseModel):
    romaji: str | None = None
    english: str | None = None
    native: str | None = None


class Anime(BaseModel):
    anilist_id: int = Field(alias="id")
    title: AnimeTitle
    season: str | None = None
    season_year: int | None = None
    status: str | None = None
    genres: list[str] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)
    description: str | None = None
    average_score: int | None = Field(alias="averageScore", default=None)
    popularity: int | None = None
    cover_image: str | None = Field(alias="coverImage", default=None)
    site_url: str | None = Field(alias="siteUrl", default=None)
    updated_at: datetime | None = Field(alias="updatedAt", default=None)

    def primary_title(self) -> str:
        return self.title.romaji or self.title.english or self.title.native or str(self.anilist_id)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Anime:
        cover_image = None
        if data.get("coverImage"):
            cover_image = data["coverImage"].get("large")
        payload = {
            "id": data.get("id"),
            "title": data.get("title") or {},
            "season": data.get("season"),
            "season_year": data.get("seasonYear"),
            "status": data.get("status"),
            "genres": data.get("genres") or [],
            "synonyms": data.get("synonyms") or [],
            "description": data.get("description"),
            "averageScore": data.get("averageScore"),
            "popularity": data.get("popularity"),
            "coverImage": cover_image,
            "siteUrl": data.get("siteUrl"),
            "updatedAt": data.get("updatedAt"),
        }
        return cls.model_validate(payload)
