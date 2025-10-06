from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest

from app.api.schemas import SettingsUpdatePayload
from app.main import get_settings_by_id, list_settings, update_settings
from tests.stubs import StubLogger
from app.core.utils import utc_now


class _RecorderMetadataClient:
    def __init__(self) -> None:
        self.enabled = True
        self.calls: list[tuple[int, int | None]] = []

    async def get_metadata(self, identifier: int, season: int | None = None) -> dict | None:
        self.calls.append((identifier, season))
        return {"id": identifier, "season": season}


class _StubSettingsRepo:
    def __init__(self) -> None:
        self._storage: dict[int, dict] = {}

    async def get(self, anilist_id: int) -> dict | None:
        entry = self._storage.get(anilist_id)
        return deepcopy(entry) if entry is not None else None

    async def upsert(self, document) -> dict:
        payload = document.model_dump()
        existing = self._storage.get(document.anilist_id)
        created_at = existing.get("created_at") if existing else payload.get("created_at") or utc_now()
        record = {
            **payload,
            "created_at": created_at,
            "updated_at": utc_now(),
            "_id": existing.get("_id") if existing else f"settings-{document.anilist_id}",
        }
        self._storage[document.anilist_id] = deepcopy(record)
        return deepcopy(record)

    async def list_all(self) -> list[dict]:
        return [deepcopy(entry) for entry in self._storage.values()]

    async def delete(self, anilist_id: int) -> int:
        return int(self._storage.pop(anilist_id, None) is not None)


class _StubAnimeRepo:
    def __init__(self, items: dict[int, dict] | None = None) -> None:
        self._items = {key: deepcopy(value) for key, value in (items or {}).items()}

    async def get_by_ids(self, ids):
        return {identifier: deepcopy(self._items[identifier]) for identifier in ids if identifier in self._items}


def _build_container(*, anime_items: dict[int, dict] | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        settings_repo=_StubSettingsRepo(),
        anime_repo=_StubAnimeRepo(anime_items),
        settings=SimpleNamespace(create_missing_save_dirs=False),
        logger=StubLogger(),
        tvdb_client=_RecorderMetadataClient(),
        tmdb_client=_RecorderMetadataClient(),
    )


@pytest.mark.asyncio
async def test_global_settings_lifecycle() -> None:
    container = _build_container()

    payload = SettingsUpdatePayload(
        save_path_template="/storage/data/{currentYear}",
        preferred_resolution="720p",
        preferred_subgroup="SubsPlease",
        tvdb_id=123,
        tvdb_season=1,
    )

    created = await update_settings(0, payload, container=container)

    assert created.settings.anilist_id == 0
    assert created.settings.enabled is False
    assert created.settings.save_path_template == "/storage/data/{currentYear}"
    assert created.settings.preferred_resolution == "720P"
    assert created.settings.preferred_subgroup == "SubsPlease"
    assert created.anime is None
    assert created.tvdb_metadata is None
    assert created.tmdb_metadata is None

    fetched = await get_settings_by_id(0, container=container)
    assert fetched.settings.save_path_template == "/storage/data/{currentYear}"
    assert fetched.anime is None
    assert fetched.tvdb_metadata is None
    assert fetched.tmdb_metadata is None

    assert container.tvdb_client.calls == []
    assert container.tmdb_client.calls == []


@pytest.mark.asyncio
async def test_settings_list_includes_global_entry() -> None:
    anime_items = {
        123: {"anilist_id": 123, "title": {"romaji": "Example"}},
    }
    container = _build_container(anime_items=anime_items)

    await update_settings(
        0,
        SettingsUpdatePayload(save_path_template="/templates/base", preferred_subgroup="Global"),
        container=container,
    )
    await update_settings(
        123,
        SettingsUpdatePayload(enabled=True, search_query="spy family"),
        container=container,
    )

    envelopes = await list_settings(container=container)
    anilist_ids = sorted(envelope.settings.anilist_id for envelope in envelopes)

    assert anilist_ids == [0, 123]
    global_envelope = next(envelope for envelope in envelopes if envelope.settings.anilist_id == 0)
    assert global_envelope.anime is None
    anime_envelope = next(envelope for envelope in envelopes if envelope.settings.anilist_id == 123)
    assert anime_envelope.anime is not None
    assert anime_envelope.settings.save_path_template == "/templates/base"
    assert anime_envelope.settings.preferred_subgroup == "Global"


@pytest.mark.asyncio
async def test_new_anime_inherits_global_defaults() -> None:
    container = _build_container()

    await update_settings(
        0,
        SettingsUpdatePayload(
            save_path_template="/root/{anime.title.english}",
            preferred_resolution="1080p",
            preferred_subgroup="SubsPlease",
            includes=["season"],
            auto_query_from_synonyms=True,
        ),
        container=container,
    )

    created = await update_settings(
        456,
        SettingsUpdatePayload(),
        container=container,
    )

    assert created.settings.anilist_id == 456
    assert created.settings.preferred_resolution == "1080P"
    assert created.settings.preferred_subgroup == "SubsPlease"
    assert created.settings.save_path_template == "/root/{anime.title.english}"
    assert created.settings.includes == ["season"]
    assert created.settings.auto_query_from_synonyms is True


@pytest.mark.asyncio
async def test_existing_settings_update_does_not_reapply_defaults() -> None:
    container = _build_container()

    await update_settings(
        0,
        SettingsUpdatePayload(preferred_subgroup="GlobalSubs"),
        container=container,
    )

    initial = await update_settings(
        789,
        SettingsUpdatePayload(preferred_subgroup="CustomSubs"),
        container=container,
    )
    assert initial.settings.preferred_subgroup == "CustomSubs"

    updated = await update_settings(
        789,
        SettingsUpdatePayload(search_query="custom query"),
        container=container,
    )

    assert updated.settings.preferred_subgroup == "CustomSubs"
    assert updated.settings.search_query == "custom query"
