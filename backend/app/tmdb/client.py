from __future__ import annotations

from time import monotonic
from typing import Any

import httpx
from structlog.stdlib import BoundLogger

from app.metrics.registry import REQUEST_LATENCY


class TMDBClient:
    """Minimal async client for The Movie Database API."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str | None,
        language: str,
        timeout_seconds: int,
        user_agent: str,
        logger: BoundLogger,
    ) -> None:
        headers = {
            "Accept": "application/json",
            "User-Agent": user_agent,
        }
        self._client = httpx.AsyncClient(base_url=base_url, headers=headers, timeout=timeout_seconds)
        self._api_key = api_key
        self._language = language
        self._logger = logger

    async def __aenter__(self) -> TMDBClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()

    @property
    def enabled(self) -> bool:
        return bool(self._api_key)

    async def get_metadata(self, tmdb_id: int, season: int | None = None) -> dict[str, Any] | None:
        if not self.enabled:
            return None

        if season is not None:
            show = await self._get(f"/tv/{tmdb_id}")
            if show:
                season_payload = await self._get(f"/tv/{tmdb_id}/season/{season}")
                return self._build_tv_payload(tmdb_id, show, season, season_payload)
            return None

        movie = await self._get(f"/movie/{tmdb_id}")
        if movie:
            return self._build_movie_payload(tmdb_id, movie)

        show = await self._get(f"/tv/{tmdb_id}")
        if show:
            return self._build_tv_payload(tmdb_id, show, None, None)

        return None

    async def _get(self, path: str) -> dict[str, Any] | None:
        if not self._api_key:
            return None
        params = {
            "api_key": self._api_key,
            "language": self._language,
        }
        try:
            start = monotonic()
            response = await self._client.get(path, params=params)
            duration = monotonic() - start
            REQUEST_LATENCY.labels("tmdb").observe(duration)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            self._logger.warning("tmdb_request_failed", path=path, error=str(exc))
            return None

    def _build_movie_payload(self, tmdb_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        release_date = payload.get("release_date")
        year = self._extract_year(release_date)
        return {
            "id": tmdb_id,
            "type": "movie",
            "title": payload.get("title"),
            "original_title": payload.get("original_title"),
            "release_date": release_date,
            "year": year,
            "overview": payload.get("overview"),
            "poster_path": payload.get("poster_path"),
            "runtime": payload.get("runtime"),
            "genres": [item.get("name") for item in payload.get("genres") or []],
        }

    def _build_tv_payload(
        self,
        tmdb_id: int,
        show_payload: dict[str, Any],
        season: int | None,
        season_payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        first_air_date = show_payload.get("first_air_date")
        year = self._extract_year(first_air_date)
        episodes = season_payload.get("episodes") if season_payload else None
        return {
            "id": tmdb_id,
            "type": "tv",
            "name": show_payload.get("name"),
            "original_name": show_payload.get("original_name"),
            "first_air_date": first_air_date,
            "year": year,
            "overview": show_payload.get("overview"),
            "poster_path": show_payload.get("poster_path"),
            "genres": [item.get("name") for item in show_payload.get("genres") or []],
            "season": season,
            "season_name": (season_payload or {}).get("name"),
            "season_overview": (season_payload or {}).get("overview"),
            "season_air_date": (season_payload or {}).get("air_date"),
            "episode_count": len(episodes) if isinstance(episodes, list) else None,
        }

    @staticmethod
    def _extract_year(value: str | None) -> int | None:
        if isinstance(value, str) and len(value) >= 4 and value[:4].isdigit():
            return int(value[:4])
        return None
