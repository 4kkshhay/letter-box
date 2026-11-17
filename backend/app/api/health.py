"""Liveness and readiness endpoints, mounted on both apps."""

import sqlite3

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.config import Settings
from app.db.connection import connect
from app.db.migrate import current_version, latest_version

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def ready(request: Request) -> JSONResponse:
    """Ready when the database exists and is migrated to this build's version."""
    settings: Settings = request.app.state.settings
    try:
        with connect(settings.database_path, read_only=True) as conn:
            version = current_version(conn)
    except sqlite3.Error:
        return JSONResponse({"status": "unavailable"}, status_code=503)
    if version != latest_version(settings.migrations_dir):
        return JSONResponse({"status": "unavailable"}, status_code=503)
    return JSONResponse({"status": "ok"})
