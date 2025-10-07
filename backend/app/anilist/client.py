from __future__ import annotations

import asyncio
from collections.abc import Iterable
from time import monotonic
from typing import Any

import httpx
from structlog.stdlib import BoundLogger

from app.anilist.models import Anime
from app.anilist.queries import ANIME_BY_ID_QUERY, ANIME_SEARCH_QUERY
from app.core.utils import utc_now
from app.metrics.registry import REQUEST_LATENCY


class AniListClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: int,
        user_agent: str,
        logger: BoundLogger,
    ) -> None:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": user_agent,
        }
        self._client = httpx.AsyncClient(
            base_url=base_url, headers=headers, timeout=timeout_seconds
        )
        self._logger = logger

    async def __aenter__(self) -> AniListClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()

    async def fetch_releasing_anime(
        self,
        season: str,
        season_year: int,
        status: str = "RELEASING",
        page_size: int = 50,
        max_retries: int = 3,
    ) -> list[Anime]:
        has_next = True
        page = 1
        results: list[Anime] = []

        while has_next:
            payload = {
                "query": ANIME_SEARCH_QUERY,
                "variables": {
                    "page": page,
                    "perPage": page_size,
                    "season": season,
                    "seasonYear": season_year,
                    "status": status,
                },
            }

            response_data = await self._request_with_retry(payload, max_retries=max_retries)
            page_data = response_data.get("data", {}).get("Page", {})
            media: Iterable[dict[str, Any]] = page_data.get("media", [])
            for entry in media:
                anime = Anime.from_api(entry)
                results.append(anime)

            page_info = page_data.get("pageInfo") or {}
            has_next = bool(page_info.get("hasNextPage"))
            page += 1

        self._logger.info(
            "anilist_fetch_complete",
            count=len(results),
            season=season,
            season_year=season_year,
            status=status,
            fetched_at=utc_now().isoformat(),
        )
        return results

    async def fetch_anime_by_id(
        self,
        anilist_id: int,
        max_retries: int = 3,
    ) -> Anime | None:
        """
        Fetch a single anime by its AniList ID.

        Args:
            anilist_id: The AniList ID of the anime to fetch
            max_retries: Maximum number of retry attempts

        Returns:
            Anime object if found, None otherwise
        """
        payload = {
            "query": ANIME_BY_ID_QUERY,
            "variables": {
                "id": anilist_id,
            },
        }

        try:
            response_data = await self._request_with_retry(payload, max_retries=max_retries)
            media_data = response_data.get("data", {}).get("Media")
            
            if not media_data:
                self._logger.warning("anilist_anime_not_found", anilist_id=anilist_id)
                return None

            anime = Anime.from_api(media_data)
            self._logger.info(
                "anilist_anime_fetched",
                anilist_id=anilist_id,
                title=anime.primary_title(),
            )
            return anime
        except Exception as exc:  # noqa: BLE001
            self._logger.error(
                "anilist_fetch_by_id_failed",
                anilist_id=anilist_id,
                error=str(exc),
            )
            return None

    async def _request_with_retry(
        self, payload: dict[str, Any], max_retries: int
    ) -> dict[str, Any]:
        for attempt in range(1, max_retries + 1):
            try:
                start = monotonic()
                response = await self._client.post("", json=payload)
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "1"))
                    await asyncio.sleep(retry_after)
                    continue
                response.raise_for_status()
                data = response.json()
                REQUEST_LATENCY.labels("anilist").observe(monotonic() - start)
                return data
            except (httpx.HTTPStatusError, httpx.TransportError) as exc:
                if attempt == max_retries:
                    self._logger.error("anilist_request_failed", attempt=attempt, error=str(exc))
                    raise
                sleep_for = min(2**attempt, 30)
                self._logger.warning(
                    "anilist_request_retry", attempt=attempt, sleep=sleep_for, error=str(exc)
                )
                await asyncio.sleep(sleep_for)
        return {}
