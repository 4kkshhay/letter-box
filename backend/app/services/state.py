"""Reads a page's saved state."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.db.connection import connect
from app.services.pages import Page


@dataclass(frozen=True)
class PageState:
    values: dict[str, Any]
    acknowledged: bool


def read_state(database_path: Path, page: Page) -> PageState:
    with connect(database_path, read_only=True) as conn:
        row = conn.execute(
            "SELECT response_json, acknowledged_at FROM page_state WHERE page = ?",
            (page.name,),
        ).fetchone()
    if row is None:
        return PageState(values={}, acknowledged=False)
    saved = json.loads(row["response_json"]) if row["response_json"] else {}
    # Only fields the page still declares are returned.
    values = {name: value for name, value in saved.items() if name in page.config.fields}
    return PageState(values=values, acknowledged=row["acknowledged_at"] is not None)
