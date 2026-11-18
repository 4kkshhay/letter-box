import json

from fastapi.testclient import TestClient

from app.config import Settings
from app.db.connection import connect
from app.admin.services import public_page_url
from app.services.pages import load_pages
from tests.conftest import ADMIN_PASSWORD, SLUG_B

ORIGIN = {"Origin": "http://testserver"}


def login(client: TestClient) -> None:
    assert client.post("/login", data={"password": ADMIN_PASSWORD}).status_code == 303


def seed_page(settings: Settings) -> None:
    with connect(settings.database_path) as conn:
        conn.execute(
            "INSERT INTO page_state (page, response_json, responded_at) VALUES (?, ?, ?)",
            ("beta", json.dumps({"choice": "b", "note": ""}), "2026-11-17T01:00:00+00:00"),
        )
        for opened, kind in (
            ("2026-11-17T00:00:00+00:00", "navigate"),
            ("2026-11-17T00:10:00+00:00", "reload"),
            ("2026-11-17T00:40:00+00:00", None),
        ):
            conn.execute(
                "INSERT INTO page_opens (page, opened_at, kind) VALUES (?, ?, ?)",
                ("beta", opened, kind),
            )


def test_dashboard_lists_pages_tracking_and_responses(
    admin_client: TestClient, with_pages: Settings
) -> None:
    seed_page(with_pages)
    login(admin_client)
    response = admin_client.get("/")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert "Alpha" in response.text
    assert "Beta" in response.text
    assert "Hidden" in response.text
    assert "Disabled" in response.text
    assert f"<code>http://localhost:8610/l/{SLUG_B}</code>" in response.text
    # Copy-only: following the public link would record a visit.
    assert f'href="http://localhost:8610/l/{SLUG_B}"' not in response.text
    assert "2026-11-17T00:00:00+00:00" in response.text
    assert "3 total · 1 new" in response.text
    assert 'class="kind fresh">New open<' in response.text
    assert 'class="kind">Refresh<' in response.text
    assert 'class="kind">Unknown<' in response.text
    assert "No response" in response.text
    assert "&#34;&#34;" in response.text or '""' in response.text


def test_admin_preview_uses_name_is_read_only_and_records_nothing(
    admin_client: TestClient, with_pages: Settings
) -> None:
    seed_page(with_pages)
    login(admin_client)
    html = admin_client.get("/view/beta")
    assert html.status_code == 200
    assert "page beta" in html.text
    payload = admin_client.get("/api/v1/pages/beta")
    assert payload.json() == {
        "title": "Beta",
        "fields": {
            "choice": {"type": "enum", "options": ["a", "b"]},
            "picks": {"type": "multi", "options": ["x", "y", "z"]},
            "note": {"type": "string", "max_length": 100},
        },
        "state": {"choice": "b", "note": ""},
        "admin": True,
    }
    assert admin_client.post("/api/v1/pages/beta/open", headers=ORIGIN).status_code == 404
    assert admin_client.patch(
        "/api/v1/pages/beta/state", json={"fields": {"choice": "a"}}, headers=ORIGIN
    ).status_code == 404
    with connect(with_pages.database_path, read_only=True) as conn:
        assert conn.execute("SELECT COUNT(*) FROM page_opens WHERE page='beta'").fetchone()[0] == 3


def test_reset_requires_same_origin_and_clears_only_page_data(
    admin_client: TestClient, with_pages: Settings
) -> None:
    seed_page(with_pages)
    login(admin_client)
    assert admin_client.post("/pages/beta/reset").status_code == 403
    response = admin_client.post("/pages/beta/reset", headers=ORIGIN)
    assert response.status_code == 303
    assert response.headers["location"] == "/view/beta"
    with connect(with_pages.database_path, read_only=True) as conn:
        assert conn.execute("SELECT COUNT(*) FROM page_state WHERE page='beta'").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM page_opens WHERE page='beta'").fetchone()[0] == 0
    assert admin_client.get("/api/v1/pages/beta").json()["state"] == {}


def test_qr_downloads_are_deterministic(admin_client: TestClient) -> None:
    login(admin_client)
    first = admin_client.get("/pages/beta/qr.png")
    second = admin_client.get("/pages/beta/qr.png")
    assert first.status_code == 200
    assert first.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert first.content == second.content
    assert first.headers["content-type"] == "image/png"
    assert "beta-qr.png" in first.headers["content-disposition"]

    svg = admin_client.get("/pages/beta/qr.svg")
    assert svg.status_code == 200
    assert b"<svg" in svg.content
    assert svg.headers["content-type"].startswith("image/svg+xml")
    assert "beta-qr.svg" in svg.headers["content-disposition"]


def test_unknown_admin_page_is_404(admin_client: TestClient) -> None:
    login(admin_client)
    assert admin_client.get("/view/missing").status_code == 404
    assert admin_client.get("/api/v1/pages/missing").status_code == 404
    assert admin_client.get("/pages/missing/qr.png").status_code == 404


def test_admin_routes_are_absent_from_public_app(public_client: TestClient) -> None:
    for path in ("/login", "/view/alpha", "/pages/alpha/qr.png"):
        response = public_client.get(path)
        assert response.status_code == 302
        assert response.headers["location"] == "/"
    assert public_client.post("/pages/alpha/reset", headers=ORIGIN).status_code == 404


def test_production_qr_url_requires_public_https_origin(with_pages: Settings) -> None:
    page = load_pages(with_pages.static_dir).by_name("beta")
    assert page is not None
    for base_url in (
        "http://letterbox.ink",
        "https://localhost",
        "https://127.0.0.2",
        "https://letterbox.ink/path",
        "javascript://letterbox.ink",
    ):
        try:
            public_page_url(base_url, page, production=True)
        except ValueError:
            pass
        else:
            raise AssertionError(f"unsafe production URL accepted: {base_url}")
    assert (
        public_page_url("https://letterbox.ink", page, production=True)
        == f"https://letterbox.ink/l/{SLUG_B}"
    )
