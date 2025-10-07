from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.base import SchedulerNotRunningError
from structlog.stdlib import BoundLogger

from app.anilist.client import AniListClient
from app.core.config import ServiceSettings
from app.db.repositories import (
    AnimeRepository,
    AnimeSettingsRepository,
    AppConfigRepository,
    QBittorrentHistoryRepository,
    TaskHistoryRepository,
    TorrentSeenRepository,
)
from app.downloader.torrent_downloader import TorrentDownloader
from app.scheduler.operations import scan_nyaa_sources, sync_anilist_catalog
from app.scraper.nyaa_client import NyaaClient
from app.tmdb.client import TMDBClient
from app.tvdb.client import TVDBClient


class SchedulerService:
    def __init__(
        self,
        scheduler: AsyncIOScheduler,
        settings: ServiceSettings,
        logger: BoundLogger,
        anime_repo: AnimeRepository,
        settings_repo: AnimeSettingsRepository,
        torrent_repo: TorrentSeenRepository,
        config_repo: AppConfigRepository,
        task_history_repo: TaskHistoryRepository,
        qbittorrent_history_repo: QBittorrentHistoryRepository,
        anilist_client: AniListClient,
        nyaa_client: NyaaClient,
        downloader: TorrentDownloader,
        tvdb_client: TVDBClient,
        tmdb_client: TMDBClient,
    ) -> None:
        self._scheduler = scheduler
        self._settings = settings
        self._logger = logger
        self._anime_repo = anime_repo
        self._settings_repo = settings_repo
        self._torrent_repo = torrent_repo
        self._config_repo = config_repo
        self._task_history_repo = task_history_repo
        self._qbittorrent_history_repo = qbittorrent_history_repo
        self._anilist_client = anilist_client
        self._nyaa_client = nyaa_client
        self._downloader = downloader
        self._tvdb_client = tvdb_client
        self._tmdb_client = tmdb_client
        self._shutdown_requested = False
        self._scheduler._shutdown_requested = False

    async def initialize(self) -> None:
        await self._anime_repo.ensure_indexes()
        await self._settings_repo.ensure_indexes()
        await self._torrent_repo.ensure_indexes()

    async def start(self) -> None:
        await self.initialize()
        self._scheduler.add_job(
            self._sync_anilist_job,
            "interval",
            seconds=self._settings.scheduler.poll_interval_seconds_anilist,
            id="sync_anilist",
            replace_existing=True,
            misfire_grace_time=60,
        )
        self._scheduler.add_job(
            self._scan_nyaa_job,
            "interval",
            seconds=self._settings.scheduler.poll_interval_seconds_nyaa,
            id="scan_nyaa",
            replace_existing=True,
            misfire_grace_time=60,
        )
        self._scheduler.start()
        self._logger.info("scheduler_started")
        self._shutdown_requested = False
        self._scheduler._shutdown_requested = False

    async def shutdown(self) -> None:
        self._shutdown_requested = True
        self._scheduler._shutdown_requested = True
        if self._scheduler.running:
            try:
                self._scheduler.shutdown(wait=False)
            except SchedulerNotRunningError:
                self._logger.debug("scheduler_already_stopped")
            else:
                self._logger.info("scheduler_stopped")

    async def _sync_anilist_job(self) -> None:
        await sync_anilist_catalog(
            settings=self._settings,
            client=self._anilist_client,
            repository=self._anime_repo,
            task_history_repo=self._task_history_repo,
            logger=self._logger.bind(job="sync_anilist"),
        )

    async def _scan_nyaa_job(self) -> None:
        await scan_nyaa_sources(
            settings=self._settings,
            anime_repo=self._anime_repo,
            settings_repo=self._settings_repo,
            torrent_repo=self._torrent_repo,
            config_repo=self._config_repo,
            task_history_repo=self._task_history_repo,
            qbittorrent_history_repo=self._qbittorrent_history_repo,
            nyaa_client=self._nyaa_client,
            downloader=self._downloader,
            tvdb_client=self._tvdb_client,
            tmdb_client=self._tmdb_client,
            logger=self._logger.bind(job="scan_nyaa"),
        )
