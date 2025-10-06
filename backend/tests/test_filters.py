from __future__ import annotations

from app.scraper.filters import NyaaFilterInput, matches_filters
from app.scraper.models import NyaaItem


def make_item(title: str, resolution: str | None = None, subgroup: str | None = None) -> NyaaItem:
    return NyaaItem(
        title=title,
        link="https://example.com/file.torrent",
        magnet=None,
        infohash="abcdef1234567890abcdef1234567890abcdef12",
        published_at=None,
        size=None,
        seeders=None,
        leechers=None,
        resolution=resolution,
        subgroup=subgroup,
    )


def test_matches_filters_with_includes_and_excludes() -> None:
    item = make_item(
        "[SubsPlease] Spy x Family - 01 (1080p)", resolution="1080P", subgroup="SubsPlease"
    )
    criteria = NyaaFilterInput(
        includes=["Spy", "1080p"],
        excludes=["Dual-Audio"],
        preferred_resolution="1080P",
        preferred_subgroup="SubsPlease",
    )
    assert matches_filters(item, criteria) is True


def test_matches_filters_rejects_wrong_resolution() -> None:
    item = make_item("[SubsPlease] Spy x Family - 01 (720p)", resolution="720P")
    criteria = NyaaFilterInput(
        includes=[], excludes=[], preferred_resolution="1080P", preferred_subgroup=None
    )
    assert matches_filters(item, criteria) is False


def test_matches_filters_rejects_excluded_term() -> None:
    item = make_item("[SubsPlease] Spy x Family - 01 (1080p) Dual-Audio", resolution="1080P")
    criteria = NyaaFilterInput(
        includes=[], excludes=["Dual-Audio"], preferred_resolution=None, preferred_subgroup=None
    )
    assert matches_filters(item, criteria) is False
