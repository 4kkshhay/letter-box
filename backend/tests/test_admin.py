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


def test_dashboard_lists_pages_only(admin_client: TestClient, with_pages: Settings) -> None:
    seed_page(with_pages)
    login(admin_client)
    response = admin_client.get("/")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    for name, title in (("alpha", "Alpha"), ("beta", "Beta"), ("hidden", "Hidden")):
        assert f'href="/pages/{name}"' in response.text
        assert title in response.text
    assert "Disabled" in response.text
    assert "Responded" in response.text
    # Seeded opens have no visitor timezone, so they show in UTC, never admin-local.
    assert "Last opened Tue 17 Nov 2026, 12:40am UTC · 3 opens" in response.text
    assert "Not opened yet" in response.text
    assert SLUG_B not in response.text
    assert "Response" not in response.text.replace("Responded", "")


def test_page_view_shows_stats_responses_and_opens_by_day(
    admin_client: TestClient, with_pages: Settings
) -> None:
    seed_page(with_pages)
    with connect(with_pages.database_path) as conn:
        conn.execute(
            "INSERT INTO page_opens (page, opened_at, kind, city, region, country, tz)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "beta",
                "2026-11-17T12:30:00+00:00",
                "navigate",
                "Wellington",
                "Wellington",
                "NZ",
                "Pacific/Auckland",
            ),
        )
    login(admin_client)
    response = admin_client.get("/pages/beta")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    text = response.text
    # Copy-only: following the public link would record an open.
    assert f"<code>http://localhost:8610/{SLUG_B}</code>" in text
    assert f'href="http://localhost:8610/{SLUG_B}"' not in text
    assert 'href="/view/beta"' in text
    assert 'href="/pages/beta/qr.png"' in text
    assert 'action="/pages/beta/reset"' in text
    # Received is the first open in local time; 4 opens, 2 of them new.
    assert "Tue 17 Nov 2026, 12:00am UTC" in text
    assert "<dd>4</dd>" in text
    assert "<dd>2</dd>" in text
    # Each open is shown in the visitor's own timezone and grouped by their date:
    # 12:30 UTC was 1:30am on 18 Nov for an Auckland visitor.
    assert "1:30am NZDT" in text
    assert "Wed 18 Nov 2026, 1:30am NZDT" in text  # last opened
    assert text.index("Wed 18 Nov 2026</h3>") < text.index("Tue 17 Nov 2026</h3>")
    assert "Wellington, NZ" in text
    assert 'class="tag good">New open<' in text
    assert 'class="tag">Refresh<' in text
    assert 'class="tag">Unknown<' in text
    assert "Location unknown" in text
    assert "choice" in text and "(empty)" in text


def test_page_view_without_activity(admin_client: TestClient, with_pages: Settings) -> None:
    login(admin_client)
    text = admin_client.get("/pages/alpha").text
    assert "No response yet." in text
    assert "Not opened yet." in text


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
    assert response.headers["location"] == "/pages/beta"
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
    assert admin_client.get("/pages/missing").status_code == 404
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
        == f"https://letterbox.ink/{SLUG_B}"
    )


def test_time_format_uses_visitor_zone_abbreviation() -> None:
    from datetime import UTC, datetime
    from zoneinfo import ZoneInfo

    from app.admin.routes import _time

    instant = datetime(2026, 11, 18, 1, 23, tzinfo=UTC)
    for zone, expected in (
        ("Pacific/Auckland", "2:23pm NZDT"),
        ("Asia/Kolkata", "6:53am IST"),
        ("Asia/Dubai", "5:23am GMT+4"),
        ("America/St_Johns", "9:53pm NST"),
        ("Asia/Kathmandu", "7:08am GMT+5:45"),
    ):
        assert _time(instant.astimezone(ZoneInfo(zone))) == expected
    assert _time(instant) == "1:23am UTC"



def test_dashboard_lists_gate_attempts_and_can_clear_them(
    admin_client: TestClient, with_pages: Settings
) -> None:
    with connect(with_pages.database_path) as conn:
        conn.execute(
            "INSERT INTO gate_attempts (attempted_at, page, correct, word, city, country, tz)"
            " VALUES ('2026-11-19T08:00:00+00:00', 'alpha', 0, '<b>tulip</b>', 'Auckland', 'NZ', 'Pacific/Auckland')"
        )
        conn.execute(
            "INSERT INTO gate_attempts (attempted_at, page, correct, word)"
            " VALUES ('2026-11-19T08:01:00+00:00', 'alpha', 1, NULL)"
        )
    login(admin_client)
    text = admin_client.get("/").text
    assert "Secret word attempts" in text
    assert "<code>&lt;b&gt;tulip&lt;/b&gt;</code>" in text  # shown as text, never HTML
    assert "Thu 19 Nov 2026</h3>" in text and "9:00pm NZDT" in text
    assert "Auckland, NZ" in text
    assert 'class="tag good">Correct ✓<' in text and 'class="tag wrong">Wrong<' in text
    assert text.index("Correct ✓") < text.index("tulip")  # newest first

    assert admin_client.post("/attempts/clear").status_code == 403
    response = admin_client.post("/attempts/clear", headers=ORIGIN)
    assert response.status_code == 303 and response.headers["location"] == "/"
    assert "No attempts yet." in admin_client.get("/").text
    with connect(with_pages.database_path, read_only=True) as conn:
        assert conn.execute("SELECT COUNT(*) FROM gate_attempts").fetchone()[0] == 0
