import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

ALLOWED_ORIGIN = "http://localhost:5173"


@pytest.fixture
def settings() -> Settings:
    """Explicit settings, so unit tests ignore any local .env file."""
    return Settings(
        _env_file=None,
        database_url="postgresql+psycopg://unused:unused@127.0.0.1:1/unused",
        cors_origins=ALLOWED_ORIGIN,
    )


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)
