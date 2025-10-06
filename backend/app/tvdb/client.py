from __future__ import annotations

import asyncio
from datetime import timedelta
from time import monotonic
from typing import Any

import httpx
from structlog.stdlib import BoundLogger

from app.core.utils import utc_now
from app.metrics.registry import REQUEST_LATENCY


class TVDBClient:
    """Thin async wrapper around TheTVDB v4 API."""

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
        self._client = httpx.AsyncClient(
            base_url=base_url, headers=headers, timeout=timeout_seconds
        )
        self._api_key = api_key
        self._language = language
        self._logger = logger
        self._token: str | None = None
        self._token_expiry = utc_now()
        self._token_lock = asyncio.Lock()

    async def __aenter__(self) -> TVDBClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()

    @property
    def enabled(self) -> bool:
        return bool(self._api_key)

    async def get_metadata(
        self, series_id: int, season: int | None = None
    ) -> dict[str, Any] | None:
        if not self.enabled:
            return None

        try:
            headers = await self._build_auth_headers()
        except Exception as exc:  # pragma: no cover - safety net
            self._logger.warning("tvdb_auth_failed", series_id=series_id, error=str(exc))
            return None
        try:
            response = await self._request("GET", f"/series/{series_id}", headers=headers)
        except httpx.HTTPError as exc:
            self._logger.warning("tvdb_fetch_failed", series_id=series_id, error=str(exc))
            return None
        if response is None:
            return None
        payload = response.json().get("data") or {}

        # Try to get translation in the specified language
        translation = await self._get_translation(series_id, headers)

        return self._transform_series_payload(series_id, payload, season, translation)

    async def _build_auth_headers(self) -> dict[str, str]:
        token = await self._get_token()
        headers = {
            "Authorization": f"Bearer {token}",
        }
        if self._language:
            headers["Accept-Language"] = self._language
        return headers

    async def _get_translation(
        self, series_id: int, headers: dict[str, str]
    ) -> dict[str, Any] | None:
        """Fetch translation for the series in the specified language."""
        if not self._language:
            return None

        try:
            response = await self._request(
                "GET",
                f"/series/{series_id}/translations/{self._language}",
                headers=headers,
            )
            if response is None:
                return None

            data = response.json().get("data")
            if data:
                return data
        except httpx.HTTPError:
            # Translation not available, continue with original name
            pass

        return None

    async def _get_token(self) -> str:
        if not self._api_key:
            raise RuntimeError("TVDB API key missing")
        if self._token and self._token_expiry > utc_now():
            return self._token
        async with self._token_lock:
            if self._token and self._token_expiry > utc_now():
                return self._token
            response = await self._request(
                "POST", "/login", json={"apikey": self._api_key}, capture_404=False
            )
            data = response.json().get("data") if response is not None else None
            token = (data or {}).get("token")
            if not token:
                raise RuntimeError("TVDB login did not return a token")
            self._token = token
            self._token_expiry = utc_now() + timedelta(hours=23)
            return token

    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        capture_404: bool = True,
    ) -> httpx.Response | None:
        start = monotonic()
        response = await self._client.request(method, url, headers=headers, json=json)
        duration = monotonic() - start
        REQUEST_LATENCY.labels("tvdb").observe(duration)
        if capture_404 and response.status_code == 404:
            return None
        response.raise_for_status()
        return response

    def _transform_series_payload(
        self,
        series_id: int,
        payload: dict[str, Any],
        season: int | None,
        translation: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        first_aired = payload.get("firstAired")
        year: int | None = None
        if isinstance(first_aired, str) and len(first_aired) >= 4 and first_aired[:4].isdigit():
            year = int(first_aired[:4])

        # Extract status name if it's a dict, otherwise use as-is
        status_raw = payload.get("status")
        status: str | None = None
        if isinstance(status_raw, dict):
            status = status_raw.get("name")
        elif isinstance(status_raw, str):
            status = status_raw

        # Get names - prefer translation if available
        original_name = payload.get("name")
        translated_name = translation.get("name") if translation else None

        # Use translated name as primary, keep both for reference
        result = {
            "id": series_id,
            "name": translated_name or original_name,  # Prefer translation
            "nameOriginal": original_name,  # Always include original
            "slug": payload.get("slug"),
            "status": status,
            "overview": translation.get("overview") if translation else payload.get("overview"),
            "first_aired": first_aired,
            "year": year,
            "image": payload.get("image"),
            "network": payload.get("network"),
            "runtime": payload.get("runtime"),
            "season": season,  # This is the configured season number from settings
        }

        # Add translated name separately if different from original
        if translated_name and translated_name != original_name:
            result["nameTranslated"] = translated_name

        return result
