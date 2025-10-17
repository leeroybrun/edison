from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EDISON_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["local", "test", "production"] = Field(default="local")

    api_title: str = "Edison API"
    api_description: str = "LLM prompt experimentation platform"
    api_version: str = "0.1.0"

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@db:5432/edison", validation_alias="DATABASE_URL"
    )

    secret_key: str = Field(default="change-me")
    access_token_expire_minutes: int = 60 * 12

    sentry_dsn: str | None = None

    allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    opentelemetry_endpoint: str | None = None

    class Paths(BaseSettings):
        model_config = SettingsConfigDict(env_prefix="EDISON_PATH_")

        base_dir: Path = Path(__file__).resolve().parents[2]
        logs_dir: Path = Path("/tmp/edison/logs")

    paths: Paths = Paths()


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
