from dataclasses import replace

from fastapi.testclient import TestClient

from app.main import create_admin_app, create_public_app
from app.security import MAX_REQUEST_BODY_BYTES, SECURITY_HEADERS
from app.services.pages import load_pages
from tests.conftest import SLUG_A


def test_security_and_no_store_headers_cover_apps_and_errors(
    public_client: TestClient, admin_client: TestClient
) -> None:
    responses = (
        public_client.get("/"),
        public_client.get("/missing"),
        public_client.get("/api/v1/missing"),
        admin_client.get("/"),
        admin_client.get("/login"),
    )
    for response in responses:
        assert response.headers["cache-control"] == "no-store"
        for name, value in SECURITY_HEADERS.items():
            assert response.headers[name] == value


def test_referrer_policy_keeps_admin_form_origin(
    public_client: TestClient, admin_client: TestClient
) -> None:
    # `no-referrer` makes browsers send `Origin: null` on form posts, which
    # would fail the admin's same-origin check for reset and sign out.
    for response in (public_client.get("/"), public_client.get("/missing")):
        assert response.headers["referrer-policy"] == "no-referrer"
    for response in (admin_client.get("/"), admin_client.get("/login")):
        assert response.headers["referrer-policy"] == "same-origin"


def test_only_hashed_assets_are_long_cached(public_client: TestClient) -> None:
    asset = public_client.get("/assets/abc123.js")
    assert asset.status_code == 200
    assert asset.headers["cache-control"] == "private, max-age=31536000, immutable"
    assert public_client.get(f"/l/{SLUG_A}").headers["cache-control"] == "no-store"


def test_production_adds_hsts(with_pages) -> None:
    settings = replace(with_pages, app_env="production", session_secret="x" * 32)
    public = TestClient(create_public_app(settings, load_pages(settings.static_dir)))
    admin = TestClient(create_admin_app(settings, load_pages(settings.static_dir)))
    expected = "max-age=31536000; includeSubDomains"
    assert public.get("/").headers["strict-transport-security"] == expected
    assert admin.get("/login").headers["strict-transport-security"] == expected


def test_coarse_body_limit_applies_before_mutations(
    public_client: TestClient, admin_client: TestClient
) -> None:
    oversized = b"x" * (MAX_REQUEST_BODY_BYTES + 1)
    opened = public_client.post(
        f"/api/v1/pages/{SLUG_A}/open",
        content=oversized,
        headers={"Origin": "http://testserver"},
    )
    login = admin_client.post(
        "/login",
        content=oversized,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert opened.status_code == login.status_code == 413
    assert opened.headers["cache-control"] == login.headers["cache-control"] == "no-store"
