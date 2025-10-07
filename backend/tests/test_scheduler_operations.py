from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.scheduler.operations import scan_nyaa_sources
from app.scraper.models import NyaaItem
from tests.stubs import StubLogger


class FakeAnimeRepo:
    def __init__(self, mapping: dict[int, dict]) -> None:
        self._mapping = mapping

    async def get_by_ids(self, ids: list[int]) -> dict[int, dict]:
        return {i: self._mapping[i] for i in ids}


class FakeSettingsRepo:
    def __init__(self, entries: list[dict]) -> None:
        self._entries = entries

    async def list_enabled(self) -> list[dict]:
        return self._entries


class FakeTorrentRepo:
    def __init__(self) -> None:
        self.seen: dict[tuple[int, str], dict] = {}

    async def exists(self, anilist_id: int, infohash: str | None, link: str) -> bool:
        key = (anilist_id, infohash or link)
        return key in self.seen

    async def mark_seen(self, document) -> dict:
        key = (document.anilist_id, document.infohash or document.link)
        payload = document.model_dump() if hasattr(document, "model_dump") else dict(document)
        self.seen[key] = payload
        return payload

    async def list_pending_for_export(
        self,
        *,
        limit: int = 50,
        anilist_id: int | None = None,
        items: list[str] | None = None,
    ) -> list[dict]:
        results = []
        for key, doc in self.seen.items():
            if doc.get("exported_to_qbittorrent"):
                continue
            if doc.get("torrent_path") is None:
                continue
            if anilist_id is not None and doc.get("anilist_id") != anilist_id:
                continue
            results.append(doc)
            if len(results) >= limit:
                break
        return results

    async def mark_exported(
        self,
        document_id,
        *,
        exported: bool,
        exported_at,
    ) -> None:
        # In tests, document_id is not used since we don't have _id
        # This is a simplified stub
        pass


class FakeNyaaClient:
    def __init__(self, items: list[NyaaItem]) -> None:
        self._items = items

    async def fetch(self, query: str) -> list[NyaaItem]:  # noqa: ARG002 - query unused
        return self._items


class FakeDownloader:
    def __init__(self, dest: Path) -> None:
        self.dest = dest
        self.downloads: list[str] = []

    async def download(self, url: str, title: str, infohash: str | None, destination: Path) -> Path:  # noqa: D401
        self.downloads.append(url)
        path = destination / f"{infohash or 'file'}.torrent"
        path.write_bytes(b"dummy")
        return path


class FakeTVDBClient:
    @property
    def enabled(self) -> bool:
        return False

    async def get_metadata(self, series_id: int, season: int | None = None) -> dict | None:  # noqa: ARG002
        return None


class FakeTMDBClient:
    @property
    def enabled(self) -> bool:
        return False

    async def get_metadata(self, tmdb_id: int, season: int | None = None) -> dict | None:  # noqa: ARG002
        return None


class FakeConfigRepo:
    """Stub config repository for testing."""

    async def get(self) -> dict | None:
        return {
            "qbittorrent_enabled": False,
            "auto_add_to_qbittorrent": False,
            "qbittorrent_torrent_template": None,
            "qbittorrent_save_template": None,
            "path_mappings": [],
        }


class FakeTaskHistoryRepo:
    """Stub task history repository for testing."""

    def __init__(self) -> None:
        self.created: list[dict] = []
        self.updated: list[tuple[str, dict]] = []

    async def create(self, document) -> dict:
        doc = document.model_dump() if hasattr(document, "model_dump") else dict(document)
        self.created.append(doc)
        doc["_id"] = len(self.created)
        return doc

    async def update(self, task_id: str, updates: dict) -> dict:
        self.updated.append((task_id, updates))
        return {"task_id": task_id, **updates}


class FakeQBittorrentHistoryRepo:
    def __init__(self) -> None:
        self.records: list[dict] = []

    async def record(self, document) -> dict:
        doc = document.model_dump() if hasattr(document, "model_dump") else dict(document)
        self.records.append(doc)
        return doc

    async def list_by_anilist(self, anilist_id: int, limit: int = 50) -> list[dict]:
        return [doc for doc in self.records if doc.get("anilist_id") == anilist_id][:limit]


@pytest.mark.asyncio
async def test_scan_nyaa_sources_downloads_once(tmp_path: Path) -> None:
    items = [
        NyaaItem(
            title="[SubsPlease] Spy x Family - 01 (1080p)",
            link="https://nyaa.si/download/12345.torrent",
            magnet=None,
            infohash="abcdef1234567890abcdef1234567890abcdef12",
            published_at=None,
            size=None,
            seeders=None,
            leechers=None,
            resolution="1080P",
            subgroup="SubsPlease",
        ),
        NyaaItem(
            title="[SubsPlease] Spy x Family - 01 (1080p)",
            link="https://nyaa.si/download/12345.torrent",
            magnet=None,
            infohash="abcdef1234567890abcdef1234567890abcdef12",
            published_at=None,
            size=None,
            seeders=None,
            leechers=None,
            resolution="1080P",
            subgroup="SubsPlease",
        ),
    ]
    save_dir = tmp_path / "downloads"
    save_dir.mkdir()
    settings = SimpleNamespace(create_missing_save_dirs=True)
    settings_repo = FakeSettingsRepo(
        [
            {
                "anilist_id": 1,
                "enabled": True,
                "save_path": str(save_dir),
                "search_query": "Spy x Family",
                "includes": ["Spy"],
                "excludes": [],
                "preferred_resolution": "1080P",
                "preferred_subgroup": "SubsPlease",
            }
        ]
    )
    anime_repo = FakeAnimeRepo({1: {"title": {"romaji": "Spy x Family"}, "synonyms": []}})
    torrent_repo = FakeTorrentRepo()
    downloader = FakeDownloader(save_dir)
    nyaa_client = FakeNyaaClient(items)
    tvdb_client = FakeTVDBClient()
    tmdb_client = FakeTMDBClient()
    task_history_repo = FakeTaskHistoryRepo()
    qbittorrent_history_repo = FakeQBittorrentHistoryRepo()

    await scan_nyaa_sources(
        settings=settings,
        anime_repo=anime_repo,
        settings_repo=settings_repo,
        torrent_repo=torrent_repo,
        config_repo=FakeConfigRepo(),
        task_history_repo=task_history_repo,
        qbittorrent_history_repo=qbittorrent_history_repo,
        nyaa_client=nyaa_client,
        downloader=downloader,
        tvdb_client=tvdb_client,
        tmdb_client=tmdb_client,
        logger=StubLogger(),
    )

    assert len(downloader.downloads) == 1
    assert (1, items[0].infohash) in torrent_repo.seen
    assert task_history_repo.created
    assert qbittorrent_history_repo.records == []
    # Ensure task was marked completed with stats
    created = task_history_repo.created[0]
    assert created["status"] == "running"
    assert task_history_repo.updated
    updated_task_id, updates = task_history_repo.updated[-1]
    assert updates["status"] == "completed"
    assert updates["items_succeeded"] >= 1
