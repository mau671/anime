from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.base import SchedulerNotRunningError
from motor.motor_asyncio import AsyncIOMotorClient
from structlog.stdlib import BoundLogger

from app.anilist.client import AniListClient
from app.core.concurrency import DomainRateLimiter, GlobalConcurrencyLimiter
from app.core.config import ServiceSettings, get_settings
from app.core.logging import configure_logging, get_logger
from app.db.mongo import create_motor_client, get_database
from app.db.repositories import (
    AnimeRepository,
    AnimeSettingsRepository,
    AppConfigRepository,
    QBittorrentHistoryRepository,
    TaskHistoryRepository,
    TorrentSeenRepository,
)
from app.downloader.torrent_downloader import TorrentDownloader
from app.metrics.registry import start_metrics_server
from app.scraper.nyaa_client import NyaaClient
from app.tmdb.client import TMDBClient
from app.tvdb.client import TVDBClient


@dataclass
class ServiceContainer:
    settings: ServiceSettings
    logger: BoundLogger
    scheduler: AsyncIOScheduler
    mongo_client: AsyncIOMotorClient
    anime_repo: AnimeRepository
    settings_repo: AnimeSettingsRepository
    torrent_repo: TorrentSeenRepository
    config_repo: AppConfigRepository
    task_history_repo: TaskHistoryRepository
    qbittorrent_history_repo: QBittorrentHistoryRepository
    anilist_client: AniListClient
    nyaa_client: NyaaClient
    downloader: TorrentDownloader
    tvdb_client: TVDBClient
    tmdb_client: TMDBClient


@asynccontextmanager
async def build_container() -> AsyncIterator[ServiceContainer]:
    settings = get_settings()
    configure_logging(settings.logging.level)
    logger = get_logger(__name__)

    if settings.metrics.enabled:
        start_metrics_server(settings.metrics.bind_host, settings.metrics.bind_port)

    motor_client = create_motor_client(settings)
    db = get_database(motor_client, settings)
    scheduler = AsyncIOScheduler(timezone="UTC")

    domain_limiter = DomainRateLimiter(settings.scheduler.rate_limit_per_domain)
    global_limiter = GlobalConcurrencyLimiter(settings.scheduler.download_concurrency)

    anilist_client = AniListClient(
        base_url=str(settings.api.base_url),
        timeout_seconds=settings.api.http_timeout_seconds,
        user_agent=settings.api.user_agent,
        logger=logger.bind(component="anilist"),
    )
    nyaa_client = NyaaClient(
        base_url=settings.nyaa.base_url,
        timeout_seconds=settings.api.http_timeout_seconds,
        user_agent=settings.api.user_agent,
        logger=logger.bind(component="nyaa"),
        domain_limiter=domain_limiter,
        global_limiter=global_limiter,
    )
    downloader = TorrentDownloader(
        timeout_seconds=settings.api.http_timeout_seconds,
        user_agent=settings.api.user_agent,
        logger=logger.bind(component="downloader"),
        domain_limiter=domain_limiter,
        global_limiter=global_limiter,
    )
    tvdb_client = TVDBClient(
        base_url=str(settings.tvdb.base_url),
        api_key=settings.tvdb.api_key,
        language=settings.tvdb.language,
        timeout_seconds=settings.api.http_timeout_seconds,
        user_agent=settings.api.user_agent,
        logger=logger.bind(component="tvdb"),
    )
    tmdb_client = TMDBClient(
        base_url=str(settings.tmdb.base_url),
        api_key=settings.tmdb.api_key,
        language=settings.tmdb.language,
        timeout_seconds=settings.api.http_timeout_seconds,
        user_agent=settings.api.user_agent,
        logger=logger.bind(component="tmdb"),
    )

    try:
        yield ServiceContainer(
            settings=settings,
            logger=logger,
            scheduler=scheduler,
            mongo_client=motor_client,
            anime_repo=AnimeRepository(db),
            settings_repo=AnimeSettingsRepository(db),
            torrent_repo=TorrentSeenRepository(db),
            config_repo=AppConfigRepository(db),
            task_history_repo=TaskHistoryRepository(db),
            qbittorrent_history_repo=QBittorrentHistoryRepository(db),
            anilist_client=anilist_client,
            nyaa_client=nyaa_client,
            downloader=downloader,
            tvdb_client=tvdb_client,
            tmdb_client=tmdb_client,
        )
    finally:
        await downloader.close()
        await nyaa_client.close()
        await anilist_client.close()
        await tvdb_client.close()
        await tmdb_client.close()
        motor_client.close()
        if scheduler.running and not getattr(scheduler, "_shutdown_requested", False):
            try:
                scheduler.shutdown(wait=False)
            except SchedulerNotRunningError:
                logger.debug("scheduler_already_stopped_on_exit")
