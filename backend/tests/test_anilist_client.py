from __future__ import annotations

import httpx
import pytest
import respx

from app.anilist.client import AniListClient
from app.anilist.models import Anime
from tests.stubs import StubLogger


@respx.mock
@pytest.mark.asyncio
async def test_fetch_releasing_anime_handles_pagination() -> None:
    route = respx.post("https://graphql.anilist.co/")
    route.side_effect = [
        httpx.Response(
            200,
            json={
                "data": {
                    "Page": {
                        "pageInfo": {"hasNextPage": True},
                        "media": [
                            {
                                "id": 1,
                                "title": {"romaji": "Spy x Family"},
                                "season": "FALL",
                                "seasonYear": 2023,
                                "status": "RELEASING",
                                "genres": ["Action"],
                                "synonyms": [],
                                "description": None,
                                "averageScore": 85,
                                "popularity": 1000,
                                "coverImage": {"large": "https://image"},
                                "siteUrl": "https://anilist.co/anime/1",
                                "updatedAt": None,
                            }
                        ],
                    }
                }
            },
        ),
        httpx.Response(
            200,
            json={
                "data": {
                    "Page": {
                        "pageInfo": {"hasNextPage": False},
                        "media": [],
                    }
                }
            },
        ),
    ]

    client = AniListClient(
        base_url="https://graphql.anilist.co",
        timeout_seconds=10,
        user_agent="test-agent",
        logger=StubLogger(),
    )

    results = await client.fetch_releasing_anime("FALL", 2023, page_size=1)
    await client.close()

    assert len(results) == 1
    assert isinstance(results[0], Anime)
    assert results[0].title.romaji == "Spy x Family"
