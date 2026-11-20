import json
import time
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.admin.auth import create_session, hash_password
from app.api.public import gate_throttle
from app.config import Settings
from app.db.connection import connect
from app.gate import (
    UNLOCK_COOKIE,
    create_unlock,
    normalize_password,
    parse_password_hashes,
)
from app.main import create_public_app
from app.services.pages import load_pages
from tests.conftest import SLUG_A, SLUG_B

ORIGIN = {"Origin": "http://testserver"}
PASSWORDS = ("Marigold", "second word")
HASHES = tuple(hash_password(normalize_password(p), salt=b"0123456789abcdef") for p in PASSWORDS)


@pytest.fixture
def gated(with_pages: Settings) -> Settings:
    (with_pages.static_dir / "recipient.json").write_text(
        json.dumps({"name": "Juniper", "hint": "it grows in spring"})
    )
    return replace(with_pages, page_password_hashes=HASHES)


@pytest.fixture
def client(gated: Settings) -> TestClient:
    gate_throttle.reset()
    return TestClient(create_public_app(gated, load_pages(gated.static_dir)), follow_redirects=False)


def guess(client: TestClient, password: str, slug: str = SLUG_A, **headers: str):
    return client.post(f"/{slug}", data={"password": password}, headers={**ORIGIN, **headers})


def opens(settings: Settings) -> int:
    with connect(settings.database_path, read_only=True) as conn:
        return conn.execute("SELECT COUNT(*) FROM page_opens").fetchone()[0]


def test_locked_link_shows_gate_and_withholds_everything(client: TestClient, gated: Settings) -> None:
    response = client.get(f"/{SLUG_A}")
    assert response.status_code == 200
    assert "Juniper" in response.text
    assert 'name="password"' in response.text
    assert "page alpha" not in response.text
    assert "it grows in spring" not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "same-origin"
    assert response.headers["x-page-gate"] == "locked"
    assert client.get(f"/api/v1/pages/{SLUG_A}").status_code == 404
    assert client.post(f"/api/v1/pages/{SLUG_A}/open", headers=ORIGIN).status_code == 404
    asset = client.get("/assets/abc123.js")
    assert asset.status_code == 302 and asset.headers["location"] == "/"
    assert opens(gated) == 0


def test_unknown_link_still_redirects_without_a_gate(client: TestClient) -> None:
    for response in (client.get("/" + "x" * 32), guess(client, "marigold", "x" * 32)):
        assert response.status_code == 302 and response.headers["location"] == "/"


def test_gate_fonts_are_public(client: TestClient) -> None:
    font = client.get("/gate/cormorant.woff2")
    assert font.status_code == 200
    assert font.headers["cache-control"] == "public, no-cache"
    assert client.get("/gate/gate.js").status_code == 200


@pytest.mark.parametrize("password", ["marigold", "  MARIGOLD ", "Marigold", "SECOND   Word"])
def test_any_configured_password_unlocks_ignoring_case_and_spacing(
    client: TestClient, password: str
) -> None:
    response = guess(client, password)
    assert response.status_code == 303
    assert response.headers["location"] == f"/{SLUG_A}"
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{UNLOCK_COOKIE}=")
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Max-Age=21600" in cookie

    page = client.get(f"/{SLUG_A}")
    assert "page alpha" in page.text and "x-page-gate" not in page.headers
    assert client.get(f"/api/v1/pages/{SLUG_A}").status_code == 200
    asset = client.get("/assets/abc123.js")
    assert asset.status_code == 200
    assert asset.headers["cache-control"] == "private, max-age=31536000, immutable"
    # The unlock is for this page only.
    assert client.get(f"/{SLUG_B}").headers["x-page-gate"] == "locked"
    assert client.get(f"/api/v1/pages/{SLUG_B}").status_code == 404


def test_wrong_password_shows_hint_after_three_misses(client: TestClient) -> None:
    for attempt in range(1, 4):
        response = guess(client, f"wrong {attempt}")
        assert response.status_code == 401
        assert "Not quite" in response.text
        assert "set-cookie" not in response.headers
        assert ("it grows in spring" in response.text) == (attempt >= 3)
    assert "page alpha" not in client.get(f"/{SLUG_A}").text


def test_unlock_requires_same_origin(client: TestClient) -> None:
    response = client.post(f"/{SLUG_A}", data={"password": "marigold"})
    assert response.status_code == 403
    assert "set-cookie" not in response.headers


def test_page_asks_again_after_thirty_minutes_but_resources_last_longer(
    client: TestClient, gated: Settings
) -> None:
    now = int(time.time())
    client.cookies.set(UNLOCK_COOKIE, create_unlock(gated.session_secret, "alpha", issued_at=now - 31 * 60))
    assert client.get(f"/{SLUG_A}").headers["x-page-gate"] == "locked"
    assert client.get(f"/api/v1/pages/{SLUG_A}").status_code == 200
    assert client.get("/assets/abc123.js").status_code == 200

    client.cookies.set(UNLOCK_COOKIE, create_unlock(gated.session_secret, "alpha", issued_at=now - 7 * 3600))
    assert client.get(f"/api/v1/pages/{SLUG_A}").status_code == 404
    assert client.get("/assets/abc123.js").status_code == 302


@pytest.mark.parametrize(
    "value",
    [
        create_unlock("another-secret", "alpha"),
        create_session("test-session-secret"),
        "v1:alpha:9999999999.forged",
        "garbage",
    ],
)
def test_forged_or_foreign_cookies_do_not_unlock(client: TestClient, value: str) -> None:
    client.cookies.set(UNLOCK_COOKIE, value)
    assert client.get(f"/{SLUG_A}").headers["x-page-gate"] == "locked"
    assert client.get("/assets/abc123.js").status_code == 302


def test_limits_are_generous_until_the_page_is_first_opened(client: TestClient, gated: Settings) -> None:
    for _ in range(19):
        assert guess(client, "wrong").status_code == 401
    # The 20th miss pauses at once, with a countdown of up to an hour.
    last = guess(client, "wrong")
    assert last.status_code == 429
    assert 'data-countdown="3600"' in last.text or 'data-countdown="3599"' in last.text
    paused = guess(client, "marigold")
    assert paused.status_code == 429
    assert "set-cookie" not in paused.headers
    # Limits are per visitor.
    assert guess(client, "marigold", **{"cf-connecting-ip": "203.0.113.9"}).status_code == 303


def test_limits_tighten_once_the_page_has_been_opened(client: TestClient, gated: Settings) -> None:
    with connect(gated.database_path) as conn:
        conn.execute(
            "INSERT INTO page_opens (page, opened_at, kind) VALUES ('alpha', '2026-11-19T00:00:00+00:00', 'navigate')"
        )
    for _ in range(4):
        assert guess(client, "wrong").status_code == 401
    assert guess(client, "wrong").status_code == 429
    assert guess(client, "marigold").status_code == 429
    # Another page that has never been opened keeps the generous limit.
    assert guess(client, "marigold", SLUG_B).status_code == 303


def test_success_clears_earlier_misses(client: TestClient) -> None:
    for _ in range(3):
        guess(client, "wrong")
    assert guess(client, "marigold").status_code == 303
    client.cookies.clear()
    assert "it grows in spring" not in guess(client, "wrong").text


def test_gate_off_without_hashes(with_pages: Settings) -> None:
    client = TestClient(create_public_app(with_pages, load_pages(with_pages.static_dir)), follow_redirects=False)
    assert "page alpha" in client.get(f"/{SLUG_A}").text
    assert client.get("/assets/abc123.js").status_code == 200
    assert guess(client, "anything").status_code == 303


def test_gate_without_recipient_greets_you(with_pages: Settings) -> None:
    settings = replace(with_pages, page_password_hashes=HASHES)
    client = TestClient(create_public_app(settings, load_pages(settings.static_dir)))
    text = client.get(f"/{SLUG_A}").text
    assert "<title>A space for you</title>" in text and ">you</h1>" in text


def test_gate_needs_a_session_secret(gated: Settings) -> None:
    with pytest.raises(RuntimeError, match="SESSION_SECRET"):
        create_public_app(replace(gated, session_secret=""), load_pages(gated.static_dir))


def test_password_hash_setting() -> None:
    assert parse_password_hashes("") == ()
    assert parse_password_hashes(f" {HASHES[0]} , {HASHES[1]},") == HASHES
    with pytest.raises(ValueError):
        parse_password_hashes(f"{HASHES[0]},not-a-hash")


def test_normalize_password() -> None:
    assert normalize_password("  MáRIGOLD\t ") == normalize_password("márigold")
    assert normalize_password("Straße") == "strasse"
    assert normalize_password("two   words") == "two words"


def attempts(settings: Settings) -> list[tuple]:
    with connect(settings.database_path, read_only=True) as conn:
        return [
            tuple(row)
            for row in conn.execute(
                "SELECT page, correct, word, city, country, tz FROM gate_attempts ORDER BY id"
            )
        ]


def test_every_entered_word_is_logged_but_correct_ones_never_as_text(
    client: TestClient, gated: Settings
) -> None:
    where = {"cf-ipcity": "Wellington", "cf-ipcountry": "NZ"}
    client.post(f"/{SLUG_A}", data={"password": "  Rose ", "tz": "Pacific/Auckland"}, headers={**ORIGIN, **where})
    client.post(f"/{SLUG_A}", data={"password": "   "}, headers=ORIGIN)  # blank: not a guess
    client.post(f"/{SLUG_A}", data={"password": "MARIGOLD", "tz": "Not/AZone"}, headers=ORIGIN)
    assert attempts(gated) == [
        ("alpha", 0, "Rose", "Wellington", "NZ", "Pacific/Auckland"),
        ("alpha", 1, None, None, None, None),
    ]


def test_paused_gate_disables_entry_and_logs_nothing(client: TestClient, gated: Settings) -> None:
    with connect(gated.database_path) as conn:
        conn.execute(
            "INSERT INTO page_opens (page, opened_at) VALUES ('alpha', '2026-11-19T00:00:00+00:00')"
        )
    for n in range(5):
        guess(client, f"wrong {n}")
    page = client.get(f"/{SLUG_A}")
    assert page.status_code == 429
    assert "a few too many tries" in page.text
    assert 'name="password"' in page.text and "disabled" in page.text
    assert "data-countdown=" in page.text
    assert "it grows in spring" in page.text  # the hint stays visible
    guess(client, "while paused")
    assert len(attempts(gated)) == 5
    # Not paused: the gate has no countdown and loads its script.
    fresh = client.get(f"/{SLUG_A}", headers={"cf-connecting-ip": "203.0.113.9"})
    assert fresh.status_code == 200 and "data-countdown" not in fresh.text
    assert 'src="/gate/gate.js"' in fresh.text


def test_retry_after_counts_down_to_the_oldest_counted_miss() -> None:
    from app.gate import GateThrottle

    throttle = GateThrottle()
    assert throttle.retry_after("v", tight=True) == 0
    for _ in range(5):
        throttle.failed("v")
    assert 899 <= throttle.retry_after("v", tight=True) <= 900
    assert throttle.retry_after("v", tight=False) == 0
    throttle.succeeded("v")
    assert throttle.retry_after("v", tight=True) == 0
