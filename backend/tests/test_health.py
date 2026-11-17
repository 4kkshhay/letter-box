import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_admin_app, create_public_app


@pytest.mark.parametrize("client_name", ["public_client", "admin_client"])
def test_health_and_ready_ok(client_name: str, request: pytest.FixtureRequest) -> None:
    client: TestClient = request.getfixturevalue(client_name)
    assert client.get("/health").json() == {"status": "ok"}
    ready = client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json() == {"status": "ok"}


def test_ready_fails_without_database(settings: Settings) -> None:
    client = TestClient(create_public_app(settings))
    assert client.get("/health").status_code == 200
    assert client.get("/health/ready").status_code == 503
    # The readiness check must not create the database as a side effect.
    assert not settings.database_path.exists()


def test_ready_fails_when_schema_is_behind(migrated: Settings) -> None:
    conn = sqlite3.connect(migrated.database_path)
    conn.execute("PRAGMA user_version = 0")
    conn.close()
    client = TestClient(create_admin_app(migrated))
    assert client.get("/health/ready").status_code == 503


@pytest.mark.parametrize("client_name", ["public_client", "admin_client"])
@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_api_docs_disabled(client_name: str, path: str, request: pytest.FixtureRequest) -> None:
    client: TestClient = request.getfixturevalue(client_name)
    assert client.get(path).status_code == 404


def test_public_root_serves_built_page_uncached(public_client: TestClient) -> None:
    response = public_client.get("/")
    assert response.status_code == 200
    assert "root page" in response.text
    assert response.headers["cache-control"] == "no-store"


def test_admin_app_does_not_serve_public_root(admin_client: TestClient) -> None:
    assert admin_client.get("/").status_code == 404
