from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import httpx
from structlog.stdlib import BoundLogger


class QBittorrentClient:
    """Async client for qBittorrent Web API."""

    def __init__(
        self,
        *,
        url: str,
        username: str | None = None,
        password: str | None = None,
        category: str = "anime",
        timeout_seconds: int = 60,
        logger: BoundLogger,
    ) -> None:
        self._url = url.rstrip("/")
        self._username = username
        self._password = password
        self._category = category
        self._timeout = timeout_seconds
        self._logger = logger
        self._client = httpx.AsyncClient(
            timeout=timeout_seconds,
            headers={"Referer": self._url},
        )
        self._authenticated = False

    async def __aenter__(self) -> QBittorrentClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()

    async def login(self) -> None:
        """Login to qBittorrent if credentials are provided."""
        if not self._username or not self._password:
            self._logger.debug("qbittorrent_no_auth", url=self._url)
            self._authenticated = True
            return

        try:
            response = await self._client.post(
                f"{self._url}/api/v2/auth/login",
                data={"username": self._username, "password": self._password},
            )

            if response.status_code == 200 and response.text.strip().lower() == "ok.":
                self._authenticated = True
                self._logger.info("qbittorrent_login_success", url=self._url)
            else:
                self._logger.error(
                    "qbittorrent_login_failed",
                    url=self._url,
                    status=response.status_code,
                    response=response.text.strip(),
                )
                raise RuntimeError(f"qBittorrent login failed: {response.text.strip()}")
        except httpx.HTTPError as exc:
            self._logger.error("qbittorrent_login_error", url=self._url, error=str(exc))
            raise RuntimeError(f"qBittorrent login error: {exc}") from exc

    async def get_version(self) -> str | None:
        """Get qBittorrent version."""
        try:
            response = await self._client.get(f"{self._url}/api/v2/app/version")
            response.raise_for_status()
            return response.text.strip()
        except httpx.HTTPError as exc:
            self._logger.error("qbittorrent_version_error", error=str(exc))
            return None

    async def add_torrent(
        self,
        torrent_path: Path,
        save_path: Path,
        category: str | None = None,
    ) -> bool:
        """
        Add a torrent file to qBittorrent.

        Args:
            torrent_path: Path to the .torrent file
            save_path: Destination path for the downloaded content
            category: Category for the torrent (defaults to configured category)

        Returns:
            True if torrent was added successfully, False otherwise
        """
        if not self._authenticated:
            await self.login()

        cat = category or self._category

        try:
            file_data = await asyncio.to_thread(torrent_path.read_bytes)

            files = {
                "torrents": (torrent_path.name, file_data, "application/x-bittorrent")
            }
            data = {
                "category": cat,
                "savepath": save_path.as_posix(),
                "autoTMM": "false",  # Disable automatic torrent management
            }

            response = await self._client.post(
                f"{self._url}/api/v2/torrents/add",
                data=data,
                files=files,
            )

            if response.status_code == 200:
                body = response.text.strip()
                self._logger.info(
                    "qbittorrent_torrent_added",
                    torrent=torrent_path.name,
                    save_path=str(save_path),
                    response=body if body else "ok",
                )
                return True
            else:
                self._logger.error(
                    "qbittorrent_add_failed",
                    torrent=torrent_path.name,
                    status=response.status_code,
                    response=response.text,
                )
                return False
        except FileNotFoundError:
            self._logger.error("qbittorrent_file_not_found", path=str(torrent_path))
            return False
        except httpx.HTTPError as exc:
            self._logger.error(
                "qbittorrent_add_error",
                torrent=torrent_path.name,
                error=str(exc),
            )
            return False

    async def get_torrents(self, category: str | None = None) -> list[dict[str, Any]]:
        """Get list of torrents, optionally filtered by category."""
        if not self._authenticated:
            await self.login()

        params = {}
        if category:
            params["category"] = category

        try:
            response = await self._client.get(
                f"{self._url}/api/v2/torrents/info",
                params=params,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            self._logger.error("qbittorrent_get_torrents_error", error=str(exc))
            return []
