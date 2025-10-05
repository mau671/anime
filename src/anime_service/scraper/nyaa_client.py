from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from time import monotonic
from urllib.parse import quote_plus, urljoin, urlparse

import httpx
from selectolax.parser import HTMLParser
from structlog.stdlib import BoundLogger

from anime_service.core.concurrency import DomainRateLimiter, GlobalConcurrencyLimiter
from anime_service.core.utils import extract_infohash, extract_resolution, extract_subgroup
from anime_service.metrics.registry import REQUEST_LATENCY
from anime_service.scraper.models import NyaaItem


class NyaaClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: int,
        user_agent: str,
        logger: BoundLogger,
        domain_limiter: DomainRateLimiter,
        global_limiter: GlobalConcurrencyLimiter,
    ) -> None:
        headers = {"User-Agent": user_agent}
        self._client = httpx.AsyncClient(
            base_url=base_url, headers=headers, timeout=timeout_seconds
        )
        self._logger = logger
        self._base_url = base_url
        self._domain_key = urlparse(base_url).netloc or base_url
        self._domain_limiter = domain_limiter
        self._global_limiter = global_limiter

    async def __aenter__(self) -> NyaaClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()

    async def fetch(self, query: str, max_retries: int = 3) -> list[NyaaItem]:
        rss_url = f"/?page=rss&q={quote_plus(query)}"
        items = await self._fetch_with_retries(
            rss_url, parser=self._parse_rss, max_retries=max_retries
        )
        if items:
            return items
        html_url = f"/?f=0&c=0_0&q={quote_plus(query)}&s=seeders&o=desc"
        return await self._fetch_with_retries(
            html_url, parser=self._parse_html, max_retries=max_retries
        )

    async def _fetch_with_retries(self, path: str, parser, max_retries: int) -> list[NyaaItem]:
        for attempt in range(1, max_retries + 1):
            try:
                async with self._global_limiter.acquire():
                    async with self._domain_limiter.limited(self._domain_key):
                        start = monotonic()
                        response = await self._client.get(path)
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "1"))
                    await asyncio.sleep(retry_after)
                    continue
                response.raise_for_status()
                items = parser(response)
                REQUEST_LATENCY.labels("nyaa").observe(monotonic() - start)
                return items
            except (httpx.HTTPError, ValueError) as exc:
                if attempt == max_retries:
                    self._logger.error("nyaa_fetch_failed", path=path, error=str(exc))
                    raise
                sleep_for = min(2**attempt, 30)
                self._logger.warning(
                    "nyaa_fetch_retry", attempt=attempt, path=path, sleep=sleep_for
                )
                await asyncio.sleep(sleep_for)
        return []

    def _parse_rss(self, response: httpx.Response) -> list[NyaaItem]:
        items: list[NyaaItem] = []
        root = ET.fromstring(response.text)
        for item in root.findall(".//item"):
            title = item.findtext("title") or ""
            link = item.findtext("link") or ""
            pub_date = item.findtext("pubDate")
            magnet = item.findtext("{https://nyaa.si/}magnetUrl") or None
            infohash = item.findtext("{https://nyaa.si/}infoHash")
            description = item.findtext("description") or ""
            size = item.findtext("{https://nyaa.si/}size")
            seeders = item.findtext("{https://nyaa.si/}seeders")
            leechers = item.findtext("{https://nyaa.si/}leechers")
            resolution = extract_resolution(title) or extract_resolution(description) or None
            subgroup = extract_subgroup(title) or extract_subgroup(description) or None

            published_at = None
            if pub_date:
                try:
                    published_at = (
                        datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
                        .astimezone(UTC)
                        .replace(tzinfo=None)
                    )
                except ValueError:
                    published_at = None

            computed_infohash = infohash or extract_infohash(description)
            if computed_infohash:
                computed_infohash = computed_infohash.lower()

            payload = {
                "title": title,
                "link": link,
                "magnet": magnet,
                "infohash": computed_infohash,
                "published_at": published_at,
                "size": size,
                "seeders": int(seeders) if seeders else None,
                "leechers": int(leechers) if leechers else None,
                "resolution": resolution,
                "subgroup": subgroup,
            }
            items.append(NyaaItem.from_payload(payload))
        return items

    def _parse_html(self, response: httpx.Response) -> list[NyaaItem]:
        items: list[NyaaItem] = []
        parser = HTMLParser(response.text)
        rows = parser.css("table.torrent-list tbody tr")
        for row in rows:
            title_link = row.css_first("td:nth-child(2) a:not(.comments)")
            if not title_link:
                continue
            title = title_link.text(strip=True)
            link = urljoin(self._base_url, title_link.attributes.get("href", ""))
            magnet_node = row.css_first("td:nth-child(3) a[href^='magnet']")
            magnet = magnet_node.attributes.get("href") if magnet_node else None
            torrent_link_node = row.css_first("td:nth-child(3) a[href$='.torrent']")
            if torrent_link_node:
                link = urljoin(self._base_url, torrent_link_node.attributes.get("href", link))
            size_node = row.css_first("td:nth-child(4)")
            seeders_node = row.css_first("td:nth-child(6)")
            leechers_node = row.css_first("td:nth-child(7)")
            date_node = row.css_first("td:nth-child(5)")

            payload = {
                "title": title,
                "link": link,
                "magnet": magnet,
                "infohash": extract_infohash(magnet or "") if magnet else None,
                "published_at": None,
                "size": size_node.text(strip=True) if size_node else None,
                "seeders": int(seeders_node.text(strip=True))
                if seeders_node and seeders_node.text(strip=True).isdigit()
                else None,
                "leechers": int(leechers_node.text(strip=True))
                if leechers_node and leechers_node.text(strip=True).isdigit()
                else None,
                "resolution": extract_resolution(title),
                "subgroup": extract_subgroup(title),
            }

            if date_node:
                payload["published_at"] = None

            items.append(NyaaItem.from_payload(payload))
        return items
