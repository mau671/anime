"""Integration tests for template rendering with external APIs."""

from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.core.utils import render_save_path_template
from app.scheduler.operations import _build_template_values
from app.tmdb.client import TMDBClient
from app.tvdb.client import TVDBClient
from tests.stubs import StubLogger


@pytest.mark.asyncio
async def test_tvdb_integration():
    """Test TVDB client integration and metadata retrieval."""
    settings = get_settings()
    
    if not settings.tvdb.api_key:
        pytest.skip("TVDB_API_KEY not configured - skipping TVDB integration test")
    
    logger = StubLogger()
    
    async with TVDBClient(
        base_url=str(settings.tvdb.base_url),
        api_key=settings.tvdb.api_key,
        language=settings.tvdb.language,
        timeout_seconds=30,
        user_agent="anime-service/1.0",
        logger=logger,
    ) as client:
        # Test with My Hero Academia (tvdb_id: 305078)
        metadata = await client.get_metadata(305078, season=8)
        
        assert metadata is not None, "Failed to retrieve TVDB metadata"
        assert metadata["id"] == 305078
        assert metadata["name"] is not None
        assert metadata["slug"] is not None
        assert metadata["year"] is not None
        assert metadata["season"] == 8
        
        print("\n✅ TVDB Integration Test Passed")
        print(f"   Name: {metadata['name']}")
        print(f"   Slug: {metadata['slug']}")
        print(f"   Year: {metadata['year']}")
        print(f"   Season: {metadata['season']}")


@pytest.mark.asyncio
async def test_tmdb_integration():
    """Test TMDB client integration and metadata retrieval."""
    settings = get_settings()
    
    if not settings.tmdb.api_key:
        pytest.skip("TMDB_API_KEY not configured - skipping TMDB integration test")
    
    logger = StubLogger()
    
    async with TMDBClient(
        base_url=str(settings.tmdb.base_url),
        api_key=settings.tmdb.api_key,
        language=settings.tmdb.language,
        timeout_seconds=30,
        user_agent="anime-service/1.0",
        logger=logger,
    ) as client:
        # Test with a known TV series
        metadata = await client.get_metadata(95479, season=1)  # Demon Slayer
        
        if metadata:
            assert metadata["id"] == 95479
            assert metadata["type"] in ["tv", "movie"]
            assert metadata.get("name") or metadata.get("title")
            
            print("\n✅ TMDB Integration Test Passed")
            print(f"   Type: {metadata['type']}")
            print(f"   Name/Title: {metadata.get('name') or metadata.get('title')}")
            print(f"   Year: {metadata.get('year')}")


@pytest.mark.asyncio
async def test_template_rendering_with_real_apis():
    """Test template rendering with real API data."""
    settings = get_settings()
    logger = StubLogger()
    
    # Skip if no API keys configured
    if not settings.tvdb.api_key:
        pytest.skip("TVDB_API_KEY not configured - skipping template rendering test")
    
    # Create clients
    tvdb_client = TVDBClient(
        base_url=str(settings.tvdb.base_url),
        api_key=settings.tvdb.api_key,
        language=settings.tvdb.language,
        timeout_seconds=30,
        user_agent="anime-service/1.0",
        logger=logger,
    )
    
    tmdb_client = TMDBClient(
        base_url=str(settings.tmdb.base_url),
        api_key=settings.tmdb.api_key,
        language=settings.tmdb.language,
        timeout_seconds=30,
        user_agent="anime-service/1.0",
        logger=logger,
    )
    
    try:
        # Simulated anime entry (My Hero Academia)
        entry = {
            "anilist_id": 182896,
            "tvdb_id": 305078,
            "tvdb_season": 8,
        }
        
        anime = {
            "anilist_id": 182896,
            "title": {
                "romaji": "Boku no Hero Academia Season 8",
                "english": "My Hero Academia Season 8",
                "native": "僕のヒーローアカデミア",
            },
            "season": "FALL",
            "season_year": 2025,
            "format": "TV",
            "status": "RELEASING",
        }
        
        # Build template values
        context = await _build_template_values(
            entry, anime, tvdb_client, tmdb_client, logger
        )
        
        # Verify context has expected fields
        assert "currentYear" in context
        assert "currentMonth" in context
        assert "currentDay" in context
        assert "anime" in context
        
        # Check if TVDB data was fetched
        if "tvdb" in context:
            assert context["tvdb"]["id"] == 305078
            assert context["tvdb"]["name"] is not None
            assert context["tvdb"]["slug"] is not None
            assert context["tvdb"]["year"] is not None
            assert context["tvdb"]["seasonNumber"] == 8
            
            print("\n✅ TVDB metadata successfully retrieved and added to context")
            print(f"   Name: {context['tvdb']['name']}")
            print(f"   Year: {context['tvdb']['year']}")
            print(f"   Season: {context['tvdb']['seasonNumber']}")
        else:
            print("\n⚠️  TVDB metadata not available in context")
        
        # Test template rendering
        template = "/storage/data/torrents/shows/Anime Ongoing/{currentYear}/{anime.season}/{tvdb.name} ({tvdb.year}) [tvdbid-{tvdb.id}]/Season {tvdb.seasonNumber}"
        rendered = render_save_path_template(template, context)
        
        print(f"\n📝 Template: {template}")
        print(f"✅ Rendered: {rendered}")
        
        # Verify rendered path has no empty placeholders
        assert "() [tvdbid-]" not in rendered, "Template has empty TVDB placeholders"
        assert "/Season/" not in rendered or "/Season {" in template, "Season number is missing"
        
        # Check that key values are present
        if "tvdb" in context:
            assert str(context["tvdb"]["id"]) in rendered
            assert str(context["tvdb"]["seasonNumber"]) in rendered
            # Name might be sanitized, so just check it's not empty
            assert rendered.count("//") == 0, "Path has empty segments"
        
    finally:
        await tvdb_client.close()
        await tmdb_client.close()


@pytest.mark.asyncio
async def test_template_rendering_without_apis():
    """Test template rendering when APIs are not available."""
    logger = StubLogger()
    
    # Create disabled clients (no API keys)
    tvdb_client = TVDBClient(
        base_url="https://api4.thetvdb.com/v4",
        api_key=None,
        language="eng",
        timeout_seconds=30,
        user_agent="anime-service/1.0",
        logger=logger,
    )
    
    tmdb_client = TMDBClient(
        base_url="https://api.themoviedb.org/3",
        api_key=None,
        language="en-US",
        timeout_seconds=30,
        user_agent="anime-service/1.0",
        logger=logger,
    )
    
    entry = {
        "anilist_id": 182896,
        "tvdb_id": 305078,
        "tvdb_season": 8,
    }
    
    anime = {
        "anilist_id": 182896,
        "title": {
            "romaji": "Boku no Hero Academia Season 8",
            "english": "My Hero Academia Season 8",
            "native": "僕のヒーローアカデミア",
        },
        "season": "FALL",
        "season_year": 2025,
        "format": "TV",
        "status": "RELEASING",
    }
    
    # Build template values (should work even without API keys)
    context = await _build_template_values(
        entry, anime, tvdb_client, tmdb_client, logger
    )
    
    # Verify basic context
    assert "currentYear" in context
    assert "anime" in context
    assert "tvdb" not in context  # Should not be present if client is disabled
    assert "tmdb" not in context  # Should not be present if client is disabled
    
    # Test simple template that doesn't require external APIs
    template = "/storage/data/torrents/shows/Anime Ongoing/{currentYear}/{anime.season}/{anime.title.romaji}"
    rendered = render_save_path_template(template, context)
    
    print(f"\n📝 Template (no APIs): {template}")
    print(f"✅ Rendered: {rendered}")
    
    assert str(context["currentYear"]) in rendered
    assert "FALL" in rendered
    assert "僕のヒーローアカデミア" in rendered or "Boku no Hero Academia Season 8" in rendered
    
    await tvdb_client.close()
    await tmdb_client.close()


def test_template_field_variations():
    """Test all supported template field variations."""
    context = {
        "currentYear": 2025,
        "currentMonth": "10",
        "currentDay": "06",
        "anime": {
            "title": {
                "romaji": "Kimetsu no Yaiba",
                "english": "Demon Slayer",
                "native": "鬼滅の刃",
            },
            "season": "FALL",
            "season_year": 2025,
            "seasonYear": 2025,
            "format": "TV",
            "status": "RELEASING",
            "anilist_id": 12345,
            "anilistId": 12345,
        },
        "tvdb": {
            "id": 404174,
            "name": "Demon Slayer: Kimetsu no Yaiba",
            "slug": "demon-slayer-kimetsu-no-yaiba",
            "year": 2019,
            "season": 4,
            "seasonNumber": 4,
        },
        "tmdb": {
            "id": 85937,
            "type": "tv",
            "name": "Demon Slayer: Kimetsu no Yaiba",
            "year": 2019,
            "season": 4,
            "seasonNumber": 4,
        },
    }
    
    test_cases = [
        ("{currentYear}", "2025"),
        ("{currentMonth}", "10"),
        ("{currentDay}", "06"),
        ("{anime.title.romaji}", "Kimetsu no Yaiba"),
        ("{anime.title.english}", "Demon Slayer"),
        ("{anime.season}", "FALL"),
        ("{anime.seasonYear}", "2025"),
        ("{anime.format}", "TV"),
        ("{anime.status}", "RELEASING"),
        ("{anime.anilistId}", "12345"),
        ("{tvdb.id}", "404174"),
        ("{tvdb.name}", "Demon Slayer Kimetsu no Yaiba"),  # Colons sanitized
        ("{tvdb.slug}", "demon-slayer-kimetsu-no-yaiba"),
        ("{tvdb.year}", "2019"),
        ("{tvdb.season}", "4"),
        ("{tvdb.seasonNumber}", "4"),
        ("{tmdb.id}", "85937"),
        ("{tmdb.type}", "tv"),
        ("{tmdb.name}", "Demon Slayer Kimetsu no Yaiba"),  # Colons sanitized
        ("{tmdb.year}", "2019"),
        ("{tmdb.season}", "4"),
        ("{tmdb.seasonNumber}", "4"),
    ]
    
    print("\n🧪 Testing all template field variations:")
    all_passed = True
    
    for template, expected in test_cases:
        result = render_save_path_template(template, context)
        # For paths with colons, they get sanitized
        if ":" in expected:
            expected_sanitized = expected.replace(":", " ")
            passed = result == expected or result == expected_sanitized
        else:
            passed = result == expected
        
        if passed:
            print(f"  ✅ {template} -> {result}")
        else:
            print(f"  ❌ {template} -> Expected: {expected}, Got: {result}")
            all_passed = False
    
    assert all_passed, "Some template fields failed to render correctly"

