from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.main import _build_settings_envelope
from tests.stubs import StubLogger


class _StubMetadataClient:
    def __init__(self, payload: dict | None, *, enabled: bool = True) -> None:
        self._payload = payload
        self.enabled = enabled
        self.calls: list[tuple[int, int | None]] = []

    async def get_metadata(self, identifier: int, season: int | None = None) -> dict | None:
        self.calls.append((identifier, season))
        return self._payload


@pytest.mark.asyncio
async def test_build_settings_envelope_includes_external_metadata() -> None:
    tvdb_payload = {"id": 456, "name": "Spy x Family", "season": 3}
    tmdb_payload = {"id": 789, "type": "tv", "title": "Spy x Family"}
    container = SimpleNamespace(
        tvdb_client=_StubMetadataClient(tvdb_payload),
        tmdb_client=_StubMetadataClient(tmdb_payload),
        logger=StubLogger(),
    )
    settings_entry = {
        "anilist_id": 123,
        "tvdb_id": 456,
        "tvdb_season": 3,
        "tmdb_id": 789,
        "tmdb_season": None,
    }
    anime_entry = {"anilist_id": 123, "title": {"english": "SPY x FAMILY"}}

    envelope = await _build_settings_envelope(container, settings_entry, anime_entry)

    assert envelope.settings.tvdb_id == 456
    assert envelope.settings.tmdb_id == 789
    assert envelope.tvdb_metadata is not None
    assert envelope.tvdb_metadata.model_dump(exclude_none=True) == tvdb_payload
    assert envelope.tmdb_metadata is not None
    assert envelope.tmdb_metadata.model_dump(exclude_none=True) == tmdb_payload

    assert container.tvdb_client.calls == [(456, 3)]
    assert container.tmdb_client.calls == [(789, None)]


@pytest.mark.asyncio
async def test_build_settings_envelope_skips_when_disabled() -> None:
    container = SimpleNamespace(
        tvdb_client=_StubMetadataClient({"id": 1}, enabled=False),
        tmdb_client=_StubMetadataClient({"id": 2}, enabled=False),
        logger=StubLogger(),
    )
    settings_entry = {
        "anilist_id": 99,
        "tvdb_id": 123,
        "tmdb_id": 456,
    }

    envelope = await _build_settings_envelope(container, settings_entry, None)

    assert envelope.settings.tvdb_id == 123
    assert envelope.tvdb_metadata is None
    assert envelope.tmdb_metadata is None
    assert container.tvdb_client.calls == []
    assert container.tmdb_client.calls == []
