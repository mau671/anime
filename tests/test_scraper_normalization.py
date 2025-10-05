from __future__ import annotations

import httpx
import pytest

from anime_service.core.concurrency import DomainRateLimiter, GlobalConcurrencyLimiter
from anime_service.scraper.nyaa_client import NyaaClient
from tests.stubs import StubLogger


@pytest.mark.asyncio
async def test_parse_rss_extracts_metadata() -> None:
    rss = """<?xml version='1.0' encoding='UTF-8'?>
    <rss xmlns:nyaa='https://nyaa.si/'>
      <channel>
        <item>
          <title>[SubsPlease] Spy x Family - 01 (1080p)</title>
          <link>https://nyaa.si/download/12345.torrent</link>
          <nyaa:infoHash>ABCDEF1234567890ABCDEF1234567890ABCDEF12</nyaa:infoHash>
          <nyaa:size>500 MiB</nyaa:size>
          <nyaa:seeders>100</nyaa:seeders>
          <nyaa:leechers>5</nyaa:leechers>
          <description>Quality release</description>
          <pubDate>Fri, 01 Sep 2023 12:00:00 +0000</pubDate>
        </item>
      </channel>
    </rss>"""
    limiter = DomainRateLimiter(4)
    global_limiter = GlobalConcurrencyLimiter(4)
    client = NyaaClient(
        base_url="https://nyaa.si",
        timeout_seconds=10,
        user_agent="test-agent",
        logger=StubLogger(),
        domain_limiter=limiter,
        global_limiter=global_limiter,
    )
    response = httpx.Response(200, text=rss, request=httpx.Request("GET", "https://nyaa.si"))
    items = client._parse_rss(response)
    await client.close()

    assert len(items) == 1
    item = items[0]
    assert item.resolution == "1080P"
    assert item.infohash == "abcdef1234567890abcdef1234567890abcdef12"
    assert item.seeders == 100
    assert item.leechers == 5
