from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import ServiceSettings


def create_motor_client(settings: ServiceSettings) -> AsyncIOMotorClient:
    kwargs: dict[str, object] = {}
    if settings.mongo.tls_ca_file:
        kwargs["tlsCAFile"] = str(settings.mongo.tls_ca_file)
    return AsyncIOMotorClient(settings.mongo.uri, **kwargs)


def get_database(client: AsyncIOMotorClient, settings: ServiceSettings) -> AsyncIOMotorDatabase:
    return client[settings.mongo.db_name]
