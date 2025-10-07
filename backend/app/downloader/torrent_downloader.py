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
        
        # Build filename with title and infohash
        if infohash:
            # Reserve space for: " " + infohash (40 chars) + ".torrent" (8 chars) = 49 chars
            # Max filename length is typically 255, so title can be max 206 chars
            max_title_length = 206
            if len(cleaned_title) > max_title_length:
                cleaned_title = cleaned_title[:max_title_length].rstrip()
            filename_parts = [cleaned_title or "torrent", infohash.lower()]
            filename = " ".join(filename_parts) + ".torrent"
        else:
            # Without infohash, leave more space for title
            max_title_length = 247  # 255 - 8 (".torrent")
            if len(cleaned_title) > max_title_length:
                cleaned_title = cleaned_title[:max_title_length].rstrip()
            filename = (cleaned_title or "torrent") + ".torrent"
        
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
