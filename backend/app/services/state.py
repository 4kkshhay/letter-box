"""A page's saved answers and recorded opens."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.db.connection import connect
from app.services.pages import EnumField, FieldDef, MultiField, Page, StringField


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class InvalidFields(Exception):
    """Submitted fields failed validation. Messages never echo submitted values."""

    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("Invalid fields")
        self.errors = errors


def _declared_only(page: Page, saved: dict[str, Any]) -> dict[str, Any]:
    """Saved values for fields the page still declares."""
    return {name: value for name, value in saved.items() if name in page.config.fields}


def read_state(database_path: Path, page: Page) -> dict[str, Any]:
    """Saved answers for the page's declared fields."""
    with connect(database_path, read_only=True) as conn:
        row = conn.execute(
            "SELECT response_json FROM page_state WHERE page = ?", (page.name,)
        ).fetchone()
    if row is None or not row["response_json"]:
        return {}
    return _declared_only(page, json.loads(row["response_json"]))


def _field_problem(field: FieldDef, value: Any) -> str | None:
    if isinstance(field, EnumField):
        if not isinstance(value, str) or value not in field.options:
            return "must be one of the options"
    elif isinstance(field, MultiField):
        if not isinstance(value, list) or not all(
            isinstance(item, str) and item in field.options for item in value
        ):
            return "must be a list of options"
        if len(set(value)) != len(value):
            return "must not repeat an option"
    elif isinstance(field, StringField):
        if not isinstance(value, str):
            return "must be text"
        if len(value) > field.max_length:
            return f"must be at most {field.max_length} characters"
    return None


def validate_fields(page: Page, submitted: dict[str, Any]) -> dict[str, Any]:
    """Check a partial update against the page's declared fields.

    `None` is always valid and means "remove the saved value".
    """
    if not submitted:
        raise InvalidFields({"fields": "at least one field is required"})
    errors: dict[str, str] = {}
    for name, value in submitted.items():
        field = page.config.fields.get(name)
        if field is None:
            errors[name] = "is not a field of this page"
        elif value is not None and (problem := _field_problem(field, value)):
            errors[name] = problem
    if errors:
        raise InvalidFields(errors)
    return submitted


def save_fields(database_path: Path, page: Page, fields: dict[str, Any]) -> dict[str, Any]:
    """Merge validated fields into the saved answers and return the result.

    json_patch merges in one statement: given keys replace saved ones, null
    removes a key, and every other saved key is kept.
    """
    with connect(database_path) as conn:
        conn.execute(
            """
            INSERT INTO page_state (page, response_json, responded_at)
            VALUES (:page, json_patch('{}', :patch), :now)
            ON CONFLICT (page) DO UPDATE SET
                response_json = json_patch(coalesce(response_json, '{}'), :patch),
                responded_at = :now
            """,
            {"page": page.name, "patch": json.dumps(fields, ensure_ascii=False), "now": utc_now()},
        )
        row = conn.execute(
            "SELECT response_json FROM page_state WHERE page = ?", (page.name,)
        ).fetchone()
    return _declared_only(page, json.loads(row["response_json"]))


def record_open(database_path: Path, page: Page) -> None:
    with connect(database_path) as conn:
        conn.execute(
            "INSERT INTO page_opens (page, opened_at) VALUES (?, ?)", (page.name, utc_now())
        )
