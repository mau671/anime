from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


class DomainRateLimiter:
    def __init__(self, max_concurrent: int) -> None:
        self._max_concurrent = max_concurrent
        self._locks: dict[str, asyncio.Semaphore] = defaultdict(
            lambda: asyncio.Semaphore(max_concurrent)
        )

    @asynccontextmanager
    async def limited(self, domain: str) -> AsyncIterator[None]:
        semaphore = self._locks[domain]
        await semaphore.acquire()
        try:
            yield
        finally:
            semaphore.release()


class GlobalConcurrencyLimiter:
    def __init__(self, bound: int) -> None:
        self._semaphore = asyncio.Semaphore(bound)

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[None]:
        await self._semaphore.acquire()
        try:
            yield
        finally:
            self._semaphore.release()
