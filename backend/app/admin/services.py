"""Database reads and writes used only by the admin app."""

import json
import ipaddress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.db.connection import connect
from app.services.pages import Page, PageRegistry
from app.services.state import read_state

OPEN_LABELS = {
    "navigate": "New open",
    "reload": "Refresh",
    "back_forward": "Back/forward",
}


@dataclass(frozen=True)
class Open:
    opened_at: str
    kind: str | None

    @property
    def label(self) -> str:
        return OPEN_LABELS.get(self.kind or "", "Unknown")

    @property
    def is_new(self) -> bool:
        """A real open rather than a refresh; unknown kinds are not counted."""
        return self.kind in {"navigate", "back_forward"}


@dataclass(frozen=True)
class AdminPage:
    page: Page
    public_url: str
    opens: list[Open]
    new_opens: int
    received_at: str | None
    has_response: bool
    response: dict[str, Any]
    responded_at: str | None


def public_page_url(public_base_url: str, page: Page, *, production: bool) -> str:
    from urllib.parse import urlsplit

    base = public_base_url.rstrip("/")
    parsed = urlsplit(base)
    local_names = {"localhost", "127.0.0.1", "::1"}
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("PUBLIC_BASE_URL must be an HTTP(S) origin")
    hostname = parsed.hostname or ""
    try:
        is_loopback = ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        is_loopback = hostname in local_names
    if production and (parsed.scheme != "https" or is_loopback):
        raise ValueError("Production PUBLIC_BASE_URL must be a non-local HTTPS URL")
    return f"{base}/l/{page.config.slug}"


def dashboard_pages(
    database_path: Path, pages: PageRegistry, public_base_url: str, *, production: bool
) -> list[AdminPage]:
    with connect(database_path, read_only=True) as conn:
        states = {
            row["page"]: row
            for row in conn.execute(
                "SELECT page, response_json, responded_at FROM page_state"
            ).fetchall()
        }
        opens_by_page: dict[str, list[Open]] = {}
        for row in conn.execute(
            "SELECT page, opened_at, kind FROM page_opens ORDER BY page, opened_at, id"
        ):
            opens_by_page.setdefault(row["page"], []).append(Open(row["opened_at"], row["kind"]))

    result = []
    for page in pages.pages:
        state = states.get(page.name)
        opens = opens_by_page.get(page.name, [])
        responded_at = state["responded_at"] if state else None
        response = json.loads(state["response_json"] or "{}") if state else {}
        result.append(
            AdminPage(
                page=page,
                public_url=public_page_url(public_base_url, page, production=production),
                opens=opens,
                new_opens=sum(1 for item in opens if item.is_new),
                received_at=opens[0].opened_at if opens else None,
                has_response=responded_at is not None,
                response=response,
                responded_at=responded_at,
            )
        )
    return result


def admin_page_payload(database_path: Path, page: Page) -> dict[str, Any]:
    return {
        "title": page.config.title,
        "fields": {name: field.model_dump() for name, field in page.config.fields.items()},
        "state": read_state(database_path, page),
        "admin": True,
    }


def reset_page(database_path: Path, page: Page) -> None:
    with connect(database_path) as conn:
        conn.execute("DELETE FROM page_state WHERE page = ?", (page.name,))
        conn.execute("DELETE FROM page_opens WHERE page = ?", (page.name,))
