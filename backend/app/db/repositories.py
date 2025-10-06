from __future__ import annotations

from collections.abc import Iterable

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.core.utils import utc_now
from app.db.models import AnimeDocument, AnimeSettingsDocument, TorrentSeenDocument


class AnimeRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["animes"]

    async def ensure_indexes(self) -> None:
        await self._collection.create_index("anilist_id", unique=True)
        await self._collection.create_index("updated_at")

    async def upsert_many(self, documents: Iterable[AnimeDocument]) -> int:
        count = 0
        for doc in documents:
            payload = doc.to_mongo()
            payload["updated_at"] = utc_now()
            await self._collection.update_one(
                {"anilist_id": doc.anilist_id},
                {"$set": payload},
                upsert=True,
            )
            count += 1
        return count

    async def all(self) -> list[dict]:
        cursor = self._collection.find()
        return [doc async for doc in cursor]

    async def get_by_ids(self, ids: Iterable[int]) -> dict[int, dict]:
        cursor = self._collection.find({"anilist_id": {"$in": list(ids)}})
        result: dict[int, dict] = {}
        async for doc in cursor:
            result[doc["anilist_id"]] = doc
        return result


class AnimeSettingsRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["anime_settings"]

    async def ensure_indexes(self) -> None:
        await self._collection.create_index("anilist_id", unique=True)
        await self._collection.create_index("enabled")

    async def get(self, anilist_id: int) -> dict | None:
        return await self._collection.find_one({"anilist_id": anilist_id})

    async def upsert(self, document: AnimeSettingsDocument) -> dict:
        doc = document.to_mongo()
        created_at = doc.pop("created_at", None)
        doc.setdefault("updated_at", utc_now())
        return await self._collection.find_one_and_update(
            {"anilist_id": document.anilist_id},
            {"$set": doc, "$setOnInsert": {"created_at": created_at or utc_now()}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )

    async def list_enabled(self) -> list[dict]:
        cursor = self._collection.find({"enabled": True, "search_query": {"$ne": None}})
        return [doc async for doc in cursor]

    async def list_all(self) -> list[dict]:
        cursor = self._collection.find()
        return [doc async for doc in cursor]

    async def delete(self, anilist_id: int) -> int:
        result = await self._collection.delete_one({"anilist_id": anilist_id})
        return result.deleted_count


class TorrentSeenRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["torrents_seen"]

    async def ensure_indexes(self) -> None:
        await self._collection.create_index("infohash", unique=True, sparse=True)
        await self._collection.create_index([("anilist_id", 1), ("link", 1)], unique=True)

    async def list_for_anilist(self, anilist_id: int, limit: int | None = None) -> list[dict]:
        cursor = self._collection.find({"anilist_id": anilist_id}).sort("saved_at", -1)
        if limit:
            cursor = cursor.limit(limit)
        return [doc async for doc in cursor]

    async def mark_seen(self, document: TorrentSeenDocument) -> dict:
        doc = document.to_mongo()
        return await self._collection.find_one_and_update(
            {"anilist_id": document.anilist_id, "link": document.link},
            {"$setOnInsert": doc},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )

    async def exists(self, anilist_id: int, infohash: str | None, link: str) -> bool:
        query = {"anilist_id": anilist_id, "$or": []}
        if infohash:
            query["$or"].append({"infohash": infohash})
        query["$or"].append({"link": link})
        return await self._collection.count_documents(query, limit=1) > 0
