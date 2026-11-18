import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.public import MAX_BODY_BYTES
from app.config import Settings
from app.db.connection import connect
from tests.conftest import ADMIN_PASSWORD, SLUG_A, SLUG_B, SLUG_DISABLED

ORIGIN = {"Origin": "http://testserver"}


def save(client: TestClient, fields: Any, slug: str = SLUG_B):
    return client.patch(f"/api/v1/pages/{slug}/state", json={"fields": fields}, headers=ORIGIN)


def saved_row(settings: Settings, page: str = "beta"):
    with connect(settings.database_path, read_only=True) as conn:
        return conn.execute("SELECT * FROM page_state WHERE page = ?", (page,)).fetchone()


def open_times(settings: Settings, page: str) -> list[str]:
    with connect(settings.database_path, read_only=True) as conn:
        rows = conn.execute("SELECT opened_at FROM page_opens WHERE page = ?", (page,))
        return [row["opened_at"] for row in rows]


# --- Saving -----------------------------------------------------------------


def test_save_returns_state_and_restores_on_next_load(public_client: TestClient) -> None:
    response = save(public_client, {"choice": "b", "picks": ["x", "z"], "note": "hello"})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    expected = {"choice": "b", "picks": ["x", "z"], "note": "hello"}
    assert response.json() == {"state": expected, "saved": True}
    assert public_client.get(f"/api/v1/pages/{SLUG_B}").json()["state"] == expected


def test_partial_update_keeps_other_fields(public_client: TestClient) -> None:
    save(public_client, {"choice": "a", "note": "first"})
    response = save(public_client, {"note": "second"})
    assert response.json()["state"] == {"choice": "a", "note": "second"}


def test_null_removes_a_saved_value(public_client: TestClient) -> None:
    save(public_client, {"choice": "a", "note": "text"})
    assert save(public_client, {"note": None}).json()["state"] == {"choice": "a"}


def test_null_for_never_saved_field_stores_nothing(public_client: TestClient) -> None:
    assert save(public_client, {"note": None}).json()["state"] == {}


def test_empty_answers_are_kept_distinct_from_no_answer(public_client: TestClient) -> None:
    state = save(public_client, {"note": "", "picks": []}).json()["state"]
    assert state == {"note": "", "picks": []}


def test_unicode_text_is_stored_as_is(public_client: TestClient, with_pages: Settings) -> None:
    save(public_client, {"note": "héllo 🌙"})
    assert json.loads(saved_row(with_pages)["response_json"]) == {"note": "héllo 🌙"}


def test_save_records_time(public_client: TestClient, with_pages: Settings) -> None:
    save(public_client, {"choice": "a"})
    assert saved_row(with_pages)["responded_at"].endswith("+00:00")


def test_text_is_returned_verbatim_not_interpreted(public_client: TestClient) -> None:
    markup = "<script>alert(1)</script>"
    assert save(public_client, {"note": markup}).json()["state"]["note"] == markup


@pytest.mark.parametrize(
    ("fields", "bad_field"),
    [
        ({"unknown": "x"}, "unknown"),
        ({"choice": "c"}, "choice"),
        ({"choice": 1}, "choice"),
        ({"choice": ["a"]}, "choice"),
        ({"picks": "x"}, "picks"),
        ({"picks": ["x", "w"]}, "picks"),
        ({"picks": ["x", "x"]}, "picks"),
        ({"picks": [1]}, "picks"),
        ({"note": 5}, "note"),
        ({"note": "x" * 101}, "note"),
        ({"note": True}, "note"),
        ({"choice": "a", "note": {"nested": 1}}, "note"),
        ({}, "fields"),
    ],
)
def test_invalid_fields_are_rejected_and_nothing_is_written(
    public_client: TestClient, with_pages: Settings, fields: dict, bad_field: str
) -> None:
    response = save(public_client, fields)
    assert response.status_code == 422
    assert bad_field in response.json()["errors"]
    assert saved_row(with_pages) is None


def test_one_bad_field_rejects_the_whole_update(
    public_client: TestClient, with_pages: Settings
) -> None:
    save(public_client, {"choice": "a"})
    assert save(public_client, {"choice": "b", "note": 7}).status_code == 422
    assert public_client.get(f"/api/v1/pages/{SLUG_B}").json()["state"] == {"choice": "a"}


def test_error_messages_do_not_echo_values(public_client: TestClient) -> None:
    body = save(public_client, {"choice": "secret-value"}).text
    assert "secret-value" not in body


@pytest.mark.parametrize(
    "body",
    ['{"fields": "x"}', '{"other": {}}', '{"fields": {}, "extra": 1}', "[]", "not json", ""],
)
def test_malformed_bodies_are_rejected(public_client: TestClient, body: str) -> None:
    response = public_client.patch(
        f"/api/v1/pages/{SLUG_B}/state",
        content=body,
        headers={**ORIGIN, "Content-Type": "application/json"},
    )
    assert response.status_code == 422


def test_non_json_content_type_is_rejected(public_client: TestClient) -> None:
    response = public_client.patch(
        f"/api/v1/pages/{SLUG_B}/state",
        content='{"fields": {"choice": "a"}}',
        headers={**ORIGIN, "Content-Type": "text/plain"},
    )
    assert response.status_code == 415


def test_oversized_body_is_rejected(public_client: TestClient, with_pages: Settings) -> None:
    response = save(public_client, {"note": "x" * (MAX_BODY_BYTES + 1)})
    assert response.status_code == 413
    assert saved_row(with_pages) is None


def test_page_without_fields_accepts_no_saves(public_client: TestClient) -> None:
    assert save(public_client, {"anything": "x"}, slug=SLUG_A).status_code == 422


def test_pages_do_not_share_state(public_client: TestClient, with_pages: Settings) -> None:
    write = save(public_client, {"choice": "a"})
    assert write.status_code == 200
    assert saved_row(with_pages, "alpha") is None


# --- Same-origin checks -----------------------------------------------------


@pytest.mark.parametrize(
    "headers",
    [{}, {"Origin": "https://evil.example"}, {"Origin": "null"}, {"Origin": "http://testserver.evil"}],
)
@pytest.mark.parametrize("action", ["state", "open"])
def test_mutations_require_same_origin(
    public_client: TestClient, with_pages: Settings, headers: dict, action: str
) -> None:
    url = f"/api/v1/pages/{SLUG_B}/{action}"
    if action == "state":
        response = public_client.patch(url, json={"fields": {"choice": "a"}}, headers=headers)
    else:
        response = public_client.post(url, headers=headers)
    assert response.status_code == 403
    assert saved_row(with_pages) is None
    assert open_times(with_pages, "beta") == []


def test_origin_scheme_may_differ_behind_a_tls_proxy(public_client: TestClient) -> None:
    response = public_client.patch(
        f"/api/v1/pages/{SLUG_B}/state",
        json={"fields": {"choice": "a"}},
        headers={"Origin": "https://testserver"},
    )
    assert response.status_code == 200


# --- Unknown and disabled pages ---------------------------------------------


@pytest.mark.parametrize("slug", ["x" * 32, SLUG_DISABLED, "beta"])
@pytest.mark.parametrize("action", ["state", "open"])
def test_mutations_on_unknown_pages_are_generic_404(
    public_client: TestClient, with_pages: Settings, slug: str, action: str
) -> None:
    url = f"/api/v1/pages/{slug}/{action}"
    if action == "state":
        response = public_client.patch(url, json={"fields": {"choice": "a"}}, headers=ORIGIN)
    else:
        response = public_client.post(url, headers=ORIGIN)
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}
    with connect(with_pages.database_path, read_only=True) as conn:
        assert conn.execute("SELECT COUNT(*) FROM page_state").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM page_opens").fetchone()[0] == 0


def test_acknowledge_endpoint_no_longer_exists(public_client: TestClient) -> None:
    response = public_client.post(f"/api/v1/pages/{SLUG_B}/acknowledge", headers=ORIGIN)
    assert response.status_code == 404


# --- Opens ------------------------------------------------------------------


def test_each_open_is_recorded_with_its_time(
    public_client: TestClient, with_pages: Settings
) -> None:
    url = f"/api/v1/pages/{SLUG_A}/open"
    assert public_client.post(url, headers=ORIGIN).status_code == 204
    assert public_client.post(url, headers=ORIGIN).status_code == 204
    times = open_times(with_pages, "alpha")
    assert len(times) == 2
    assert all(time.endswith("+00:00") for time in times)
    assert open_times(with_pages, "beta") == []


@pytest.mark.parametrize("kind", ["navigate", "reload", "back_forward"])
def test_open_stores_navigation_kind(
    public_client: TestClient, with_pages: Settings, kind: str
) -> None:
    url = f"/api/v1/pages/{SLUG_A}/open?kind={kind}"
    assert public_client.post(url, headers=ORIGIN).status_code == 204
    with connect(with_pages.database_path, read_only=True) as conn:
        assert conn.execute("SELECT kind FROM page_opens").fetchone()["kind"] == kind


def test_open_without_kind_is_stored_as_unknown(
    public_client: TestClient, with_pages: Settings
) -> None:
    assert public_client.post(f"/api/v1/pages/{SLUG_A}/open", headers=ORIGIN).status_code == 204
    with connect(with_pages.database_path, read_only=True) as conn:
        assert conn.execute("SELECT kind FROM page_opens").fetchone()["kind"] is None


@pytest.mark.parametrize("kind", ["prerender", "", "RELOAD", "x" * 500])
def test_open_with_unknown_kind_is_rejected(
    public_client: TestClient, with_pages: Settings, kind: str
) -> None:
    response = public_client.post(f"/api/v1/pages/{SLUG_A}/open?kind={kind}", headers=ORIGIN)
    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid input"}
    assert open_times(with_pages, "alpha") == []


def test_open_changes_nothing_else(public_client: TestClient, with_pages: Settings) -> None:
    public_client.post(f"/api/v1/pages/{SLUG_B}/open", headers=ORIGIN)
    assert saved_row(with_pages) is None


def test_loading_a_page_records_no_open(public_client: TestClient, with_pages: Settings) -> None:
    public_client.get(f"/l/{SLUG_A}")
    public_client.head(f"/l/{SLUG_A}")
    public_client.get(f"/api/v1/pages/{SLUG_A}")
    assert open_times(with_pages, "alpha") == []


# --- Admin app --------------------------------------------------------------


def test_admin_app_has_no_public_mutations(admin_client: TestClient) -> None:
    assert admin_client.post("/login", data={"password": ADMIN_PASSWORD}).status_code == 303
    assert admin_client.post(f"/api/v1/pages/{SLUG_B}/open", headers=ORIGIN).status_code == 404
    assert (
        admin_client.patch(
            f"/api/v1/pages/{SLUG_B}/state", json={"fields": {"choice": "a"}}, headers=ORIGIN
        ).status_code
        == 404
    )
