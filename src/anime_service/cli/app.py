from __future__ import annotations

import asyncio
from pathlib import Path

import typer
import uvicorn

from anime_service.core.bootstrap import build_container
from anime_service.core.utils import ensure_directory, sanitize_save_path
from anime_service.db.models import AnimeSettingsDocument
from anime_service.scheduler.operations import scan_nyaa_sources, sync_anilist_catalog
from anime_service.scheduler.service import SchedulerService

cli = typer.Typer(help="Anime torrent monitoring utility")

SEASON_OPTION = typer.Option(None)
YEAR_OPTION = typer.Option(None)
LIMIT_OPTION = typer.Option(20)
ANILIST_ID_OPTION = typer.Option(...)
SAVE_PATH_OPTION = typer.Option(None)
SEARCH_QUERY_OPTION = typer.Option(None)
INCLUDE_OPTION = typer.Option(None, help="Include filters")
EXCLUDE_OPTION = typer.Option(None, help="Exclude filters")
PREFERRED_RESOLUTION_OPTION = typer.Option(None)
PREFERRED_SUBGROUP_OPTION = typer.Option(None)
ENABLE_OPTION = typer.Option(False, help="Enable tracking")
ONCE_OPTION = typer.Option(False, help="Run a single scan")


@cli.command()
def init_db() -> None:
    async def _run() -> None:
        async with build_container() as container:
            await container.anime_repo.ensure_indexes()
            await container.settings_repo.ensure_indexes()
            await container.torrent_repo.ensure_indexes()
            container.logger.info("database_initialized")

    asyncio.run(_run())


@cli.command()
def sync_anilist(
    season: str | None = SEASON_OPTION,
    year: int | None = YEAR_OPTION,
) -> None:
    async def _run() -> None:
        async with build_container() as container:
            await container.anime_repo.ensure_indexes()
            await sync_anilist_catalog(
                settings=container.settings,
                client=container.anilist_client,
                repository=container.anime_repo,
                logger=container.logger,
                season=season,
                season_year=year,
            )

    asyncio.run(_run())


@cli.command()
def list_animes(limit: int = LIMIT_OPTION) -> None:
    async def _run() -> None:
        async with build_container() as container:
            animes = await container.anime_repo.all()
            for anime in animes[:limit]:
                title = anime.get("title", {})
                primary = (
                    title.get("romaji")
                    or title.get("english")
                    or title.get("native")
                    or anime.get("anilist_id")
                )
                typer.echo(f"{anime['anilist_id']}: {primary}")

    asyncio.run(_run())


@cli.command()
def set_settings(
    anilist_id: int = ANILIST_ID_OPTION,
    save_path: Path | None = SAVE_PATH_OPTION,
    search_query: str | None = SEARCH_QUERY_OPTION,
    include: list[str] | None = INCLUDE_OPTION,
    exclude: list[str] | None = EXCLUDE_OPTION,
    preferred_resolution: str | None = PREFERRED_RESOLUTION_OPTION,
    preferred_subgroup: str | None = PREFERRED_SUBGROUP_OPTION,
    enable: bool = ENABLE_OPTION,
) -> None:
    async def _run() -> None:
        async with build_container() as container:
            resolved_path = str(sanitize_save_path(save_path)) if save_path else None
            if resolved_path:
                ensure_directory(
                    Path(resolved_path),
                    create=container.settings.create_missing_save_dirs,
                    logger=container.logger,
                )

            await container.settings_repo.ensure_indexes()
            payload = {
                "anilist_id": anilist_id,
                "enabled": enable,
                "save_path": resolved_path,
                "search_query": search_query,
            }
            if include is not None:
                payload["includes"] = [item.strip() for item in include if item.strip()]
            if exclude is not None:
                payload["excludes"] = [item.strip() for item in exclude if item.strip()]
            if preferred_resolution:
                payload["preferred_resolution"] = preferred_resolution.upper()
            if preferred_subgroup:
                payload["preferred_subgroup"] = preferred_subgroup
            document = AnimeSettingsDocument(**payload)
            await container.settings_repo.upsert(document)
            container.logger.info("settings_updated", anilist_id=anilist_id)

    asyncio.run(_run())


@cli.command()
def scan_nyaa(once: bool = ONCE_OPTION) -> None:
    async def _run() -> None:
        async with build_container() as container:
            await container.anime_repo.ensure_indexes()
            await container.settings_repo.ensure_indexes()
            await container.torrent_repo.ensure_indexes()
            await scan_nyaa_sources(
                settings=container.settings,
                anime_repo=container.anime_repo,
                settings_repo=container.settings_repo,
                torrent_repo=container.torrent_repo,
                nyaa_client=container.nyaa_client,
                downloader=container.downloader,
                logger=container.logger,
            )
            if not once:
                scheduler = SchedulerService(
                    scheduler=container.scheduler,
                    settings=container.settings,
                    logger=container.logger,
                    anime_repo=container.anime_repo,
                    settings_repo=container.settings_repo,
                    torrent_repo=container.torrent_repo,
                    anilist_client=container.anilist_client,
                    nyaa_client=container.nyaa_client,
                    downloader=container.downloader,
                )
                await scheduler.start()
                try:
                    await asyncio.Event().wait()
                except (KeyboardInterrupt, asyncio.CancelledError):
                    pass
                finally:
                    await scheduler.shutdown()

    asyncio.run(_run())


@cli.command()
def run_service() -> None:
    async def _run() -> None:
        async with build_container() as container:
            scheduler_service = SchedulerService(
                scheduler=container.scheduler,
                settings=container.settings,
                logger=container.logger,
                anime_repo=container.anime_repo,
                settings_repo=container.settings_repo,
                torrent_repo=container.torrent_repo,
                anilist_client=container.anilist_client,
                nyaa_client=container.nyaa_client,
                downloader=container.downloader,
            )
            await scheduler_service.start()
            config = uvicorn.Config(
                "anime_service.api.server:app",
                host="0.0.0.0",
                port=8000,
                loop="asyncio",
                reload=False,
            )
            server = uvicorn.Server(config)

            server_task = asyncio.create_task(server.serve())
            try:
                await server_task
            except (KeyboardInterrupt, asyncio.CancelledError):
                server.should_exit = True
                await server_task
            finally:
                await scheduler_service.shutdown()

    asyncio.run(_run())
