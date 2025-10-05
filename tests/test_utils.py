from __future__ import annotations

from anime_service.core import utils


def test_sanitize_filename_removes_invalid_chars() -> None:
    original = 'Spy/Family:*"?'
    expected = "Spy Family"
    assert utils.sanitize_filename(original) == expected


def test_extract_resolution_detects_value() -> None:
    text = "[SubsPlease] Spy x Family - 01 (1080p)"
    assert utils.extract_resolution(text) == "1080P"


def test_extract_subgroup_detects_value() -> None:
    text = "[SubsPlease] Spy x Family"
    assert utils.extract_subgroup(text) == "SubsPlease"


def test_include_exclude_filters() -> None:
    text = "[SubsPlease] Spy x Family - 01 (1080p)"
    assert utils.any_includes(text, ["Spy", "1080p"])
    assert utils.any_excludes(text, ["Family"]) is True
    assert utils.any_excludes(text, ["Dual-Audio"]) is False


def test_extract_infohash_from_text() -> None:
    text = "magnet:?xt=urn:btih:ABCDEF1234567890ABCDEF1234567890ABCDEF12"
    assert utils.extract_infohash(text) == "abcdef1234567890abcdef1234567890abcdef12"
