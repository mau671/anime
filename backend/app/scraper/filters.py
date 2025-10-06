from __future__ import annotations

from collections.abc import Iterable

from app.core.utils import any_excludes, any_includes
from app.scraper.models import NyaaItem


class NyaaFilterInput:
    def __init__(
        self,
        includes: Iterable[str],
        excludes: Iterable[str],
        preferred_resolution: str | None,
        preferred_subgroup: str | None,
    ) -> None:
        self.includes = list(includes or [])
        self.excludes = list(excludes or [])
        self.preferred_resolution = preferred_resolution
        self.preferred_subgroup = preferred_subgroup


def matches_filters(item: NyaaItem, criteria: NyaaFilterInput) -> bool:
    title = item.title
    if criteria.includes and not any_includes(title, criteria.includes):
        return False
    if criteria.excludes and any_excludes(title, criteria.excludes):
        return False

    if criteria.preferred_resolution and item.resolution:
        if item.resolution.upper() != criteria.preferred_resolution.upper():
            return False

    if criteria.preferred_subgroup and item.subgroup:
        if item.subgroup.lower() != criteria.preferred_subgroup.lower():
            return False

    return True
