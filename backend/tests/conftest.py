from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.bootstrap import build_container

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

    container_manager = build_container()
    container = await container_manager.__aenter__()
    app.state.container = container

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        await container_manager.__aexit__(None, None, None)
        app.state.container = None


@pytest_asyncio.fixture
async def config_repo(client: AsyncClient) -> AsyncIterator:  # noqa: ANN001 - type provided via return
    """Repository for app config tied to the running container."""
    from app.main import app

    repo = app.state.container.config_repo
    try:
        yield repo
    finally:
        await app.state.container.mongo_client.drop_database(repo._collection.database.name)
