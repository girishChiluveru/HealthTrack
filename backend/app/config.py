import re
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    """Application settings, read from the environment and then `backend/.env`."""

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    # SecretStr keeps these values out of reprs and logs.
    database_url: SecretStr
    jwt_secret: SecretStr = Field(min_length=32)
    # Limited to HMAC algorithms, since the signing key is a shared secret.
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    cors_origins: Annotated[list[str], NoDecode]
    # Optional. Without a key the app works as normal and AI insights say so.
    ai_provider: Literal["groq", "openrouter"] = "groq"
    ai_api_key: SecretStr | None = None
    ai_model: str | None = None
    # At most 30, so the browser's 40-second limit always outlasts it.
    ai_timeout_seconds: float = Field(default=30, gt=0, le=30)

    @field_validator("database_url", mode="before")
    @classmethod
    def use_psycopg_driver(cls, value: object) -> object:
        # Hosts give plain URLs, which SQLAlchemy would pair with a driver not installed here.
        return (
            re.sub(r"^postgres(ql)?://", "postgresql+psycopg://", value)
            if isinstance(value, str)
            else value
        )

    @field_validator("ai_api_key", mode="before")
    @classmethod
    def blank_key_means_none(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        items = value.split(",") if isinstance(value, str) else value
        origins = [origin.strip() for origin in items if origin.strip()]
        if "*" in origins:
            raise ValueError("CORS_ORIGINS must list explicit origins, not a wildcard")
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
