from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import AnyUrl, BaseModel, HttpUrl


class NyaaItem(BaseModel):
    title: str
    link: HttpUrl
    magnet: AnyUrl | None = None
    infohash: str | None = None
    published_at: datetime | None = None
    size: str | None = None
    seeders: int | None = None
    leechers: int | None = None
    resolution: str | None = None
    subgroup: str | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> NyaaItem:
        return cls.model_validate(payload)
