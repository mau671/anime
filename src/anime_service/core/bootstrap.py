from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.base import SchedulerNotRunningError
from structlog.stdlib import BoundLogger

from anime_service.anilist.client import AniListClient
from anime_service.core.concurrency import DomainRateLimiter, GlobalConcurrencyLimiter
from anime_service.core.config import ServiceSettings, get_settings
from anime_service.core.logging import configure_logging, get_logger
from anime_service.db.mongo import create_motor_client, get_database
from anime_service.db.repositories import (
    AnimeRepository,
    AnimeSettingsRepository,
    TorrentSeenRepository,
)
from anime_service.downloader.torrent_downloader import TorrentDownloader
from anime_service.metrics.registry import start_metrics_server
from anime_service.scraper.nyaa_client import NyaaClient


@dataclass
class ServiceContainer:
    settings: ServiceSettings
    logger: BoundLogger
    scheduler: AsyncIOScheduler
    anime_repo: AnimeRepository
    settings_repo: AnimeSettingsRepository
    torrent_repo: TorrentSeenRepository
    anilist_client: AniListClient
    nyaa_client: NyaaClient
    downloader: TorrentDownloader


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

    try:
        yield ServiceContainer(
            settings=settings,
            logger=logger,
            scheduler=scheduler,
            anime_repo=AnimeRepository(db),
            settings_repo=AnimeSettingsRepository(db),
            torrent_repo=TorrentSeenRepository(db),
            anilist_client=anilist_client,
            nyaa_client=nyaa_client,
            downloader=downloader,
        )
    finally:
        await downloader.close()
        await nyaa_client.close()
        await anilist_client.close()
        motor_client.close()
        if scheduler.running:
            try:
                scheduler.shutdown(wait=False)
            except SchedulerNotRunningError:
                logger.debug("scheduler_already_stopped_on_exit")
