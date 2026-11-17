from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.db.migrate import run_migrations
from app.main import create_admin_app, create_public_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Settings pointing at an empty temp directory; the database does not exist yet."""
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<!doctype html><p>root page</p>")
    return replace(
        get_settings(),
        database_path=tmp_path / "data" / "test.db",
        static_dir=static_dir,
    )


@pytest.fixture
def migrated(settings: Settings) -> Settings:
    run_migrations(settings.database_path, settings.migrations_dir)
    return settings


@pytest.fixture
def public_client(migrated: Settings) -> TestClient:
    return TestClient(create_public_app(migrated))


@pytest.fixture
def admin_client(migrated: Settings) -> TestClient:
    return TestClient(create_admin_app(migrated))
