"""Tests that need a running PostgreSQL. Run them with `pytest -m integration`."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import get_settings
from app.database import get_session_factory
from app.main import create_app

pytestmark = pytest.mark.integration


def test_database_health_with_real_postgres() -> None:
    client = TestClient(create_app(get_settings()))

    response = client.get("/api/health/db")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_connected_server_is_postgres_16() -> None:
    with get_session_factory()() as session:
        version = session.execute(text("SHOW server_version")).scalar_one()

    assert version.startswith("16.")
