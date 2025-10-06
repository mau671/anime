from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Async HTTP client for API testing."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def config_repo() -> AsyncIterator:
    """Repository for app config with test database."""
    from app.core.config import get_settings
    from app.db.repositories import AppConfigRepository

    settings = get_settings()
    test_db_name = f"{settings.mongo.db_name}_test"

    client = AsyncIOMotorClient(settings.mongo.uri)
    db = client[test_db_name]
    repo = AppConfigRepository(db)

    try:
        yield repo
    finally:
        # Clean up test database
        await client.drop_database(test_db_name)
        client.close()
