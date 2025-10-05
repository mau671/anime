from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, BaseModel, Field, HttpUrl, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class APISettings(BaseModel):
    base_url: HttpUrl = Field(default="https://graphql.anilist.co")
    season: Literal["WINTER", "SPRING", "SUMMER", "FALL"] = Field(default="FALL")
    season_year: PositiveInt | None = None
    user_agent: str = Field(default="anime-service/1.0")
    http_timeout_seconds: PositiveInt = Field(default=30)
    auto_query_from_synonyms: bool = Field(default=False)


class SchedulerSettings(BaseModel):
    poll_interval_seconds_anilist: PositiveInt = Field(default=3600)
    poll_interval_seconds_nyaa: PositiveInt = Field(default=300)
    download_concurrency: PositiveInt = Field(default=4)
    rate_limit_per_domain: PositiveInt = Field(default=4)


class MongoSettings(BaseModel):
    uri: str = Field(
        validation_alias=AliasChoices("MONGODB_URI", "MONGO__URI", "uri")
    )
    db_name: str = Field(
        validation_alias=AliasChoices("MONGODB_DB_NAME", "MONGO__DB_NAME", "db_name")
    )
    tls_ca_file: Path | None = Field(default=None)


class NyaaSettings(BaseModel):
    base_url: str = Field(default="https://nyaa.si")


class LoggingSettings(BaseModel):
    level: str = Field(default="INFO")


class MetricsSettings(BaseModel):
    enabled: bool = Field(default=True)
    bind_host: str = Field(default="0.0.0.0")
    bind_port: int = Field(default=8001)


class ServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_nested_delimiter="__"
    )

    api: APISettings = Field(default_factory=APISettings)
    scheduler: SchedulerSettings = Field(default_factory=SchedulerSettings)
    mongo: MongoSettings
    nyaa: NyaaSettings = Field(default_factory=NyaaSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    metrics: MetricsSettings = Field(default_factory=MetricsSettings)

    create_missing_save_dirs: bool = Field(default=True)


@lru_cache(maxsize=1)
def get_settings() -> ServiceSettings:
    return ServiceSettings()
