from dataclasses import replace

from fastapi.testclient import TestClient

from app.admin.auth import (
    SESSION_COOKIE,
    LoginThrottle,
    create_session,
    hash_password,
    valid_session,
    verify_password,
)
from app.main import create_admin_app
from app.services.pages import load_pages
from tests.conftest import ADMIN_PASSWORD


def test_password_hash_is_salted_and_verifies() -> None:
    first = hash_password("a long password")
    second = hash_password("a long password")
    assert first.startswith("scrypt$")
    assert first != second
    assert verify_password("a long password", first)
    assert not verify_password("wrong", first)
    assert not verify_password("anything", "not-a-valid-hash")


def test_signed_session_rejects_tampering_and_expiry() -> None:
    session = create_session("secret", issued_at=1000)
    assert valid_session(session, "secret", now=1001)
    assert not valid_session(session + "x", "secret", now=1001)
    assert not valid_session(session, "other-secret", now=1001)
    assert not valid_session(session, "secret", now=1000 + 12 * 60 * 60 + 1)


def test_protected_routes_require_login(admin_client: TestClient) -> None:
    assert admin_client.get("/").status_code == 303
    assert admin_client.get("/").headers["location"] == "/login"
    assert admin_client.get("/view/alpha").status_code == 303
    api = admin_client.get("/api/v1/pages/alpha")
    assert api.status_code == 401
    assert api.headers["cache-control"] == "no-store"
    assert admin_client.get("/health/ready").status_code == 200


def test_login_sets_protected_session_and_logout_clears_it(admin_client: TestClient) -> None:
    failed = admin_client.post("/login", data={"password": "wrong"})
    assert failed.status_code == 401
    assert "Incorrect password" in failed.text

    response = admin_client.post("/login", data={"password": ADMIN_PASSWORD})
    assert response.status_code == 303
    assert response.headers["location"] == "/"
    cookie = response.headers["set-cookie"]
    assert f"{SESSION_COOKIE}=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=strict" in cookie
    assert admin_client.get("/").status_code == 200

    logged_out = admin_client.post("/logout", headers={"Origin": "http://testserver"})
    assert logged_out.status_code == 303
    assert logged_out.headers["location"] == "/login"
    assert admin_client.get("/").status_code == 303


def test_login_cookie_is_secure_in_production(with_pages) -> None:
    settings = replace(with_pages, app_env="production")
    settings = replace(settings, session_secret="x" * 32)
    client = TestClient(
        create_admin_app(settings, load_pages(settings.static_dir)),
        follow_redirects=False,
        base_url="https://testserver",
    )
    response = client.post("/login", data={"password": ADMIN_PASSWORD})
    assert "Secure" in response.headers["set-cookie"]


def test_admin_refuses_missing_credentials(with_pages) -> None:
    for settings in (
        replace(with_pages, admin_password_hash=""),
        replace(with_pages, session_secret=""),
        replace(with_pages, app_env="production", session_secret="short"),
    ):
        try:
            create_admin_app(settings, load_pages(settings.static_dir))
        except RuntimeError:
            pass
        else:
            raise AssertionError("invalid admin credentials were accepted")


def test_login_is_throttled_after_repeated_failures(admin_client: TestClient) -> None:
    for _ in range(5):
        assert admin_client.post("/login", data={"password": "wrong"}).status_code == 401
    assert admin_client.post("/login", data={"password": ADMIN_PASSWORD}).status_code == 429


def test_throttle_window_can_recover() -> None:
    limiter = LoginThrottle(attempts=1, window_seconds=0)
    limiter.failed()
    assert limiter.allowed()
