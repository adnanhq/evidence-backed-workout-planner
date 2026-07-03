"""Service configuration, sourced from environment / services/engine/.env."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from protocol_engine import settings as engine_settings


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(engine_settings.ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    protocol_model: str = Field(default=engine_settings.DEFAULT_MODEL, alias="PROTOCOL_MODEL")
    protocol_fallback_model: str = Field(
        default=engine_settings.DEFAULT_FALLBACK_MODEL, alias="PROTOCOL_FALLBACK_MODEL"
    )
    protocol_data_dir: str = Field(default="", alias="PROTOCOL_DATA_DIR")
    allowed_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        alias="ALLOWED_ORIGINS",
    )
    max_concurrency: int = Field(default=2, alias="MAX_CONCURRENCY")

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
