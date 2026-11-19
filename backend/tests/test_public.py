import json

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.db.connection import connect
from tests.conftest import SLUG_A, SLUG_B, SLUG_DISABLED


def _is_redirect_to_root(response) -> bool:
    return response.status_code == 302 and response.headers["location"] == "/"


def test_link_serves_its_own_page_uncached(public_client: TestClient) -> None:
    alpha = public_client.get(f"/{SLUG_A}")
    beta = public_client.get(f"/{SLUG_B}")
    assert alpha.status_code == beta.status_code == 200
    assert "page alpha" in alpha.text
    assert "page beta" in beta.text
    assert alpha.headers["cache-control"] == "no-store"


def test_old_l_links_redirect_to_the_page_address(public_client: TestClient) -> None:
    for method in (public_client.get, public_client.head):
        response = method(f"/l/{SLUG_A}")
        assert response.status_code == 302
        assert response.headers["location"] == f"/{SLUG_A}"
        assert response.headers["cache-control"] == "no-store"


def test_fixed_routes_still_win_over_links(public_client: TestClient) -> None:
    assert public_client.get("/health").status_code == 200
    assert public_client.get("/assets/abc123.js").status_code == 200


def test_head_request_on_link_is_allowed(public_client: TestClient) -> None:
    assert public_client.head(f"/{SLUG_A}").status_code == 200


@pytest.mark.parametrize(
    "path",
    [
        "/" + "x" * 32,
        f"/{SLUG_DISABLED}",
        f"/{SLUG_A}/",
        f"/{SLUG_A}/extra",
        "/l/" + "x" * 32,
        f"/l/{SLUG_DISABLED}",
        f"/l/{SLUG_A}/",
        "/l/",
        "/l/alpha",
        "/health/extra",
        "/alpha",
        "/pages/alpha/index.html",
        "/pages/alpha/page.json",
        "/assets/",
        "/assets/missing.js",
        "/assets/../pages/alpha/page.json",
        "/index.html",
        "/robots.txt",
        "/admin",
    ],
)
def test_unknown_paths_all_redirect_to_root(public_client: TestClient, path: str) -> None:
    response = public_client.get(path)
    assert _is_redirect_to_root(response)
    assert response.headers["cache-control"] == "no-store"
    assert response.text == ""


def test_unknown_and_disabled_links_are_indistinguishable(public_client: TestClient) -> None:
    unknown = public_client.get("/" + "x" * 32)
    disabled = public_client.get(f"/{SLUG_DISABLED}")
    assert unknown.status_code == disabled.status_code
    assert unknown.content == disabled.content
    assert dict(unknown.headers) == dict(disabled.headers)


def test_assets_are_served(public_client: TestClient) -> None:
    response = public_client.get("/assets/abc123.js")
    assert response.status_code == 200
    assert "asset" in response.text


def test_bootstrap_returns_config_and_empty_state(public_client: TestClient) -> None:
    response = public_client.get(f"/api/v1/pages/{SLUG_B}")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "title": "Beta",
        "fields": {
            "choice": {"type": "enum", "options": ["a", "b"]},
            "picks": {"type": "multi", "options": ["x", "y", "z"]},
            "note": {"type": "string", "max_length": 100},
        },
        "state": {},
    }


def test_bootstrap_never_exposes_slug_or_name(public_client: TestClient) -> None:
    body = public_client.get(f"/api/v1/pages/{SLUG_B}").text
    assert SLUG_B not in body
    assert "beta" not in body


def test_bootstrap_returns_saved_state_for_declared_fields_only(
    public_client: TestClient, with_pages: Settings
) -> None:
    saved = {"choice": "b", "removed_field": "old"}
    with connect(with_pages.database_path) as conn:
        conn.execute(
            "INSERT INTO page_state (page, response_json) VALUES (?, ?)",
            ("beta", json.dumps(saved)),
        )
    body = public_client.get(f"/api/v1/pages/{SLUG_B}").json()
    assert body["state"] == {"choice": "b"}
    # Another page's state is unaffected.
    assert public_client.get(f"/api/v1/pages/{SLUG_A}").json()["state"] == {}


@pytest.mark.parametrize("key", ["x" * 32, SLUG_DISABLED, "alpha", "beta"])
def test_bootstrap_for_unknown_link_is_generic_404(public_client: TestClient, key: str) -> None:
    response = public_client.get(f"/api/v1/pages/{key}")
    unmatched = public_client.get("/api/v1/nothing")
    assert response.status_code == unmatched.status_code == 404
    assert response.json() == unmatched.json() == {"detail": "Not Found"}


def test_get_requests_write_nothing(public_client: TestClient, with_pages: Settings) -> None:
    public_client.get(f"/{SLUG_B}")
    public_client.get(f"/api/v1/pages/{SLUG_B}")
    with connect(with_pages.database_path, read_only=True) as conn:
        assert conn.execute("SELECT COUNT(*) FROM page_state").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM page_opens").fetchone()[0] == 0
