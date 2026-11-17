import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.db.migrate import run_migrations
from app.main import create_admin_app, create_public_app
from app.services.pages import load_pages

SLUG_A = "a" * 32
SLUG_B = "b" * 32
SLUG_DISABLED = "d" * 32


def write_page(static_dir: Path, name: str, config: Any, *, html: bool = True) -> Path:
    """Write a built page the way the frontend build does."""
    page_dir = static_dir / "pages" / name
    page_dir.mkdir(parents=True)
    content = config if isinstance(config, str) else json.dumps(config)
    (page_dir / "page.json").write_text(content)
    if html:
        (page_dir / "index.html").write_text(f"<!doctype html><p>page {name}</p>")
    return page_dir


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Settings pointing at an empty temp directory; the database does not exist yet."""
    static_dir = tmp_path / "static"
    (static_dir / "assets").mkdir(parents=True)
    (static_dir / "index.html").write_text("<!doctype html><p>root page</p>")
    (static_dir / "assets" / "abc123.js").write_text("console.log('asset')")
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
def with_pages(migrated: Settings) -> Settings:
    write_page(migrated.static_dir, "alpha", {"slug": SLUG_A, "title": "Alpha"})
    write_page(
        migrated.static_dir,
        "beta",
        {
            "slug": SLUG_B,
            "title": "Beta",
            "fields": {
                "choice": {"type": "enum", "options": ["a", "b"]},
                "picks": {"type": "multi", "options": ["x", "y", "z"]},
                "note": {"type": "string", "max_length": 100},
            },
        },
    )
    write_page(
        migrated.static_dir,
        "hidden",
        {"slug": SLUG_DISABLED, "title": "Hidden", "enabled": False},
    )
    return migrated


@pytest.fixture
def public_client(with_pages: Settings) -> TestClient:
    app = create_public_app(with_pages, load_pages(with_pages.static_dir))
    return TestClient(app, follow_redirects=False)


@pytest.fixture
def admin_client(with_pages: Settings) -> TestClient:
    app = create_admin_app(with_pages, load_pages(with_pages.static_dir))
    return TestClient(app, follow_redirects=False)
