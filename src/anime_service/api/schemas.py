from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field


class SettingsUpdatePayload(BaseModel):
    enabled: bool | None = None
    save_path: str | None = None
    search_query: str | None = None
    includes: list[str] | None = None
    excludes: list[str] | None = None
    preferred_resolution: Annotated[
        str | None, Field(pattern=r"^(480p|720p|1080p|2160p|4K)$", default=None)
    ] = None
    preferred_subgroup: str | None = None
    auto_query_from_synonyms: bool | None = None
