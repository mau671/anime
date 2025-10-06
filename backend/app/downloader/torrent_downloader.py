from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import httpx
from structlog.stdlib import BoundLogger

from app.core.concurrency import DomainRateLimiter, GlobalConcurrencyLimiter
from app.core.utils import sanitize_filename, write_bytes_atomically


class TorrentDownloader:
    def __init__(
        self,
        timeout_seconds: int,
        user_agent: str,
        logger: BoundLogger,
        domain_limiter: DomainRateLimiter,
        global_limiter: GlobalConcurrencyLimiter,
    ) -> None:
        headers = {"User-Agent": user_agent}
        self._client = httpx.AsyncClient(headers=headers, timeout=timeout_seconds)
        self._logger = logger
        self._domain_limiter = domain_limiter
        self._global_limiter = global_limiter

    async def close(self) -> None:
        await self._client.aclose()

    async def download(self, url: str, title: str, infohash: str | None, destination: Path) -> Path:
        cleaned_title = sanitize_filename(title)
        filename_parts = [cleaned_title or (infohash or "torrent")]
        if infohash:
            filename_parts.append(infohash.lower())
        filename = " ".join(filename_parts).strip() + ".torrent"
        filepath = destination / filename

        domain = urlparse(url).netloc or "torrent_download"

        async with self._global_limiter.acquire():
            async with self._domain_limiter.limited(domain):
                response = await self._client.get(url)
        response.raise_for_status()
        content = response.content
        if not content:
            raise ValueError("Downloaded torrent is empty")

        await write_bytes_atomically(filepath, content)
        self._logger.info("torrent_downloaded", url=url, path=str(filepath), size=len(content))
        return filepath
