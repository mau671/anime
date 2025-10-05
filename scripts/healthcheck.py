from __future__ import annotations

import asyncio

import httpx


async def main() -> int:
    async with httpx.AsyncClient(timeout=5) as client:
        response = await client.get("http://127.0.0.1:8000/health")
        response.raise_for_status()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
