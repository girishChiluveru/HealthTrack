from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import URL, Connection, Engine, create_engine, make_url, text
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.main import create_app

ALLOWED_ORIGIN = "http://localhost:5173"
BACKEND_DIR = Path(__file__).resolve().parents[1]


def register_and_login(client: TestClient, email: str, role: str = "patient") -> dict[str, str]:
    credentials = {"email": email, "password": "correct-horse-battery"}
    client.post("/api/auth/register", json={"name": "Asha Rao", "role": role, **credentials})
    login = client.post("/api/auth/login", json=credentials)
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def build_settings(**overrides: object) -> Settings:
    """Explicit settings, so tests ignore any local .env file."""
    values = {
        "database_url": "postgresql+psycopg://unused:unused@127.0.0.1:1/unused",
        "jwt_secret": "test-only-secret-with-at-least-32-characters",
        "cors_origins": ALLOWED_ORIGIN,
        "ai_api_key": None,
    }
    return Settings(_env_file=None, **(values | overrides))


@pytest.fixture
def settings() -> Settings:
    return build_settings()


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture
def mock_db(app: FastAPI) -> MagicMock:
    """Replace the database session for tests that must not need PostgreSQL."""
    session = MagicMock()
    app.dependency_overrides[get_db] = lambda: session
    return session


# Fixtures below need PostgreSQL. Only tests marked `integration` should use them.


def alembic_config(database_url: URL) -> Config:
    config = Config(BACKEND_DIR / "alembic.ini")
    config.attributes["database_url"] = database_url.render_as_string(hide_password=False)
    return config


@contextmanager
def temporary_database(name: str) -> Iterator[URL]:
    """Create an empty database beside the development one, and drop it afterwards."""
    assert name.endswith("_test"), "Refusing to manage a database not named *_test"
    server_url = make_url(get_settings().database_url.get_secret_value())
    admin = create_engine(server_url, isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
            connection.execute(text(f'CREATE DATABASE "{name}"'))
        yield server_url.set(database=name)
    finally:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


@pytest.fixture(scope="session")
def test_engine() -> Iterator[Engine]:
    """A database built by the real migrations, never by `create_all()`."""
    with temporary_database("healthtrack_test") as url:
        command.upgrade(alembic_config(url), "head")
        engine = create_engine(url)
        yield engine
        engine.dispose()


@pytest.fixture
def db_connection(test_engine: Engine) -> Iterator[Connection]:
    with test_engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        transaction.rollback()


@pytest.fixture
def db_session(db_connection: Connection) -> Iterator[Session]:
    """A session whose commits become savepoints, so each test's writes are rolled back."""
    with Session(bind=db_connection, join_transaction_mode="create_savepoint") as session:
        yield session


@pytest.fixture
def db_client(app: FastAPI, db_session: Session) -> TestClient:
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app)
