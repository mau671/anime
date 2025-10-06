from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, PositiveInt, model_validator
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
    uri: str
    db_name: str
    tls_ca_file: Path | None = Field(default=None)


class NyaaSettings(BaseModel):
    base_url: str = Field(default="https://nyaa.si")


class LoggingSettings(BaseModel):
    level: str = Field(default="INFO")


class MetricsSettings(BaseModel):
    enabled: bool = Field(default=True)
    bind_host: str = Field(default="0.0.0.0")
    bind_port: int = Field(default=8001)


class TVDBSettings(BaseModel):
    base_url: HttpUrl = Field(default="https://api4.thetvdb.com/v4")
    api_key: str | None = Field(default=None, validation_alias="TVDB_API_KEY")
    language: str = Field(default="eng")


class TMDBSettings(BaseModel):
    base_url: HttpUrl = Field(default="https://api.themoviedb.org/3")
    api_key: str | None = Field(default=None, validation_alias="TMDB_API_KEY")
    language: str = Field(default="en-US")


class ServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_nested_delimiter="__"
    )

    api: APISettings = Field(default_factory=APISettings)
    scheduler: SchedulerSettings = Field(default_factory=SchedulerSettings)
    mongo: MongoSettings | None = None
    mongo_uri: str = Field(
        default="mongodb://127.0.0.1:27017",
        validation_alias="MONGODB_URI",
    )
    mongo_db_name: str = Field(
        default="app",
        validation_alias="MONGODB_DB_NAME",
    )
    mongo_tls_ca_file: Path | None = Field(default=None)
    nyaa: NyaaSettings = Field(default_factory=NyaaSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    metrics: MetricsSettings = Field(default_factory=MetricsSettings)
    tvdb: TVDBSettings = Field(default_factory=TVDBSettings)
    tmdb: TMDBSettings = Field(default_factory=TMDBSettings)
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
    )

    create_missing_save_dirs: bool = Field(default=True)

    @model_validator(mode="after")
    def _populate_mongo(self) -> ServiceSettings:
        if self.mongo is None:
            self.mongo = MongoSettings(
                uri=self.mongo_uri,
                db_name=self.mongo_db_name,
                tls_ca_file=self.mongo_tls_ca_file,
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> ServiceSettings:
    return ServiceSettings()
