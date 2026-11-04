from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.database import get_db


def override_db(app: FastAPI, session: MagicMock) -> None:
    app.dependency_overrides[get_db] = lambda: session


def test_health_reports_api_running(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "healthtrack-api"}


def test_database_health_when_connected(app: FastAPI, client: TestClient) -> None:
    override_db(app, MagicMock())

    response = client.get("/api/health/db")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_database_health_when_connection_fails(app: FastAPI, client: TestClient) -> None:
    session = MagicMock()
    session.execute.side_effect = OperationalError(
        "SELECT 1", {}, Exception("connection to db-secret-host failed")
    )
    override_db(app, session)

    response = client.get("/api/health/db")

    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "unavailable"}
    assert "db-secret-host" not in response.text
