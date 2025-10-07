from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.core.utils import utc_now
from app.db.models import (
    AnimeDocument,
    AnimeSettingsDocument,
    AppConfigDocument,
    QBittorrentHistoryDocument,
    TaskHistoryDocument,
    TorrentSeenDocument,
)


class AnimeRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["animes"]

    async def ensure_indexes(self) -> None:
        await self._collection.create_index("anilist_id", unique=True)
        await self._collection.create_index("updated_at")

    async def upsert_many(self, documents: Iterable[AnimeDocument]) -> int:
        count = 0
        for doc in documents:
            payload = doc.model_dump(by_alias=True, exclude_none=True)
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
        doc = document.model_dump(by_alias=True, exclude_none=True)
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
        doc = document.model_dump(by_alias=True, exclude_none=True)
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

    async def list_pending_for_export(
        self,
        *,
        limit: int = 50,
        anilist_id: int | None = None,
        items: list[str] | None = None,
    ) -> list[dict]:
        query: dict[str, Any] = {
            "exported_to_qbittorrent": {"$ne": True},
            "torrent_path": {"$ne": None},
        }
        if anilist_id is not None:
            query["anilist_id"] = anilist_id
        if items:
            query["$or"] = [
                {"torrent_path": {"$in": items}},
                {"link": {"$in": items}},
                {"infohash": {"$in": items}},
            ]
        cursor = self._collection.find(query).sort("seen_at", 1).limit(limit)
        return [doc async for doc in cursor]

    async def mark_exported(
        self,
        document_id,
        *,
        exported: bool,
        exported_at: datetime | None,
    ) -> None:
        await self._collection.update_one(
            {"_id": document_id},
            {
                "$set": {
                    "exported_to_qbittorrent": exported,
                    "exported_at": exported_at,
                    "updated_at": utc_now(),
                }
            },
        )


class AppConfigRepository:
    """Repository for application-wide configuration."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["app_config"]

    async def ensure_indexes(self) -> None:
        await self._collection.create_index("config_key", unique=True)

    async def get(self) -> dict | None:
        """Get the application configuration (singleton document)."""
        return await self._collection.find_one({"config_key": "app_config"})

    async def upsert(self, document: AppConfigDocument) -> dict:
        """Update or create the application configuration."""
        doc = document.to_mongo_dict()
        doc["config_key"] = "app_config"  # Ensure singleton key
        created_at = doc.pop("created_at", None)
        doc["updated_at"] = utc_now()

        return await self._collection.find_one_and_update(
            {"config_key": "app_config"},
            {"$set": doc, "$setOnInsert": {"created_at": created_at or utc_now()}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )


class TaskHistoryRepository:
    """Repository for task execution history."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["task_history"]

    async def ensure_indexes(self) -> None:
        await self._collection.create_index("task_id", unique=True)
        await self._collection.create_index("task_type")
        await self._collection.create_index("status")
        await self._collection.create_index("trigger")
        await self._collection.create_index("started_at")
        await self._collection.create_index("anilist_id", sparse=True)
        # Compound index for efficient queries
        await self._collection.create_index([("task_type", 1), ("started_at", -1)])

    async def create(self, document: TaskHistoryDocument) -> dict:
        """Create a new task history record."""
        doc = document.to_mongo_dict()
        result = await self._collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def update(self, task_id: str, updates: dict) -> dict | None:
        """Update a task history record."""
        updates["updated_at"] = utc_now()
        return await self._collection.find_one_and_update(
            {"task_id": task_id},
            {"$set": updates},
            return_document=ReturnDocument.AFTER,
        )

    async def get_by_id(self, task_id: str) -> dict | None:
        """Get a task by its ID."""
        return await self._collection.find_one({"task_id": task_id})

    async def list_recent(
        self,
        limit: int = 50,
        task_type: str | None = None,
        status: str | None = None,
        anilist_id: int | None = None,
    ) -> list[dict]:
        """List recent tasks with optional filters."""
        query = {}
        if task_type:
            query["task_type"] = task_type
        if status:
            query["status"] = status
        if anilist_id is not None:
            query["anilist_id"] = anilist_id

        cursor = self._collection.find(query).sort("started_at", -1).limit(limit)
        return [doc async for doc in cursor]

    async def get_running_tasks(self) -> list[dict]:
        """Get all currently running tasks."""
        cursor = self._collection.find({"status": "running"}).sort("started_at", -1)
        return [doc async for doc in cursor]

    async def get_statistics(
        self,
        task_type: str | None = None,
        since: datetime | None = None,
    ) -> dict:
        """Get statistics for tasks."""
        match_stage = {}
        if task_type:
            match_stage["task_type"] = task_type
        if since:
            match_stage["started_at"] = {"$gte": since}

        pipeline = []
        if match_stage:
            pipeline.append({"$match": match_stage})

        pipeline.append(
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1},
                    "total_processed": {"$sum": "$items_processed"},
                    "total_succeeded": {"$sum": "$items_succeeded"},
                    "total_failed": {"$sum": "$items_failed"},
                }
            }
        )

        result = await self._collection.aggregate(pipeline).to_list(length=None)
        return {item["_id"]: item for item in result}


class QBittorrentHistoryRepository:
    """Repository storing torrents pushed to qBittorrent."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["qbittorrent_history"]

    async def ensure_indexes(self) -> None:
        await self._collection.create_index("anilist_id")
        await self._collection.create_index("created_at")

    async def record(self, document: QBittorrentHistoryDocument) -> dict:
        doc = document.to_mongo_dict()
        result = await self._collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def list_by_anilist(
        self,
        anilist_id: int,
        limit: int = 50,
    ) -> list[dict]:
        cursor = (
            self._collection.find({"anilist_id": anilist_id})
            .sort("created_at", -1)
            .limit(limit)
        )
        return [doc async for doc in cursor]
