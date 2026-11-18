"""Database reads and writes used only by the admin app."""

import ipaddress
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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
    opened_at: datetime
    kind: str | None
    city: str | None = None
    region: str | None = None
    country: str | None = None

    @property
    def label(self) -> str:
        return OPEN_LABELS.get(self.kind or "", "Unknown")

    @property
    def is_new(self) -> bool:
        """A real open rather than a refresh; unknown kinds are not counted."""
        return self.kind in {"navigate", "back_forward"}

    @property
    def location(self) -> str | None:
        parts: list[str] = []
        for part in (self.city, self.region, self.country):
            if part and part not in parts:
                parts.append(part)
        return ", ".join(parts) or None


@dataclass(frozen=True)
class PageSummary:
    """One row of the dashboard list."""

    page: Page
    total_opens: int
    last_opened: datetime | None
    has_response: bool


@dataclass(frozen=True)
class PageDetail:
    page: Page
    public_url: str
    opens: list[Open]
    has_response: bool
    response: dict[str, Any]
    responded_at: datetime | None

    @property
    def received_at(self) -> datetime | None:
        return min((item.opened_at for item in self.opens), default=None)

    @property
    def last_opened(self) -> datetime | None:
        return max((item.opened_at for item in self.opens), default=None)

    @property
    def new_opens(self) -> int:
        return sum(1 for item in self.opens if item.is_new)

    @property
    def opens_by_day(self) -> list[tuple[date, list[Open]]]:
        """Opens grouped by the visitor's local date, newest first."""
        days: dict[date, list[Open]] = {}
        for item in sorted(self.opens, key=lambda o: o.opened_at, reverse=True):
            days.setdefault(item.opened_at.date(), []).append(item)
        return list(days.items())


def _local(value: str, tz_name: str | None) -> datetime:
    """A stored UTC time in the visitor's own timezone, or UTC if unknown."""
    try:
        tz = ZoneInfo(tz_name) if tz_name else UTC
    except (ZoneInfoNotFoundError, ValueError):
        tz = UTC
    return datetime.fromisoformat(value).astimezone(tz)


def public_page_url(public_base_url: str, page: Page, *, production: bool) -> str:
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


def page_summaries(database_path: Path, pages: PageRegistry) -> list[PageSummary]:
    with connect(database_path, read_only=True) as conn:
        totals = {
            row["page"]: row["total"]
            for row in conn.execute("SELECT page, COUNT(*) AS total FROM page_opens GROUP BY page")
        }
        last = {
            row["page"]: _local(row["opened_at"], row["tz"])
            for row in conn.execute(
                "SELECT page, opened_at, tz FROM page_opens AS o WHERE id = ("
                " SELECT id FROM page_opens WHERE page = o.page"
                " ORDER BY opened_at DESC, id DESC LIMIT 1)"
            )
        }
        responded = {
            row["page"]
            for row in conn.execute("SELECT page FROM page_state WHERE responded_at IS NOT NULL")
        }
    result = []
    for page in pages.pages:
        result.append(
            PageSummary(
                page=page,
                total_opens=totals.get(page.name, 0),
                last_opened=last.get(page.name),
                has_response=page.name in responded,
            )
        )
    return result


def page_detail(
    database_path: Path, page: Page, public_base_url: str, *, production: bool
) -> PageDetail:
    with connect(database_path, read_only=True) as conn:
        state = conn.execute(
            "SELECT response_json, responded_at, responded_tz FROM page_state WHERE page = ?",
            (page.name,),
        ).fetchone()
        opens = [
            Open(
                opened_at=_local(row["opened_at"], row["tz"]),
                kind=row["kind"],
                city=row["city"],
                region=row["region"],
                country=row["country"],
            )
            for row in conn.execute(
                "SELECT opened_at, kind, city, region, country, tz FROM page_opens"
                " WHERE page = ? ORDER BY opened_at, id",
                (page.name,),
            )
        ]
    responded_at = state["responded_at"] if state else None
    return PageDetail(
        page=page,
        public_url=public_page_url(public_base_url, page, production=production),
        opens=opens,
        has_response=responded_at is not None,
        response=json.loads(state["response_json"] or "{}") if state else {},
        responded_at=_local(responded_at, state["responded_tz"]) if responded_at else None,
    )


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
