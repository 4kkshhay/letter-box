"""Builds the two ASGI apps: public (pages) and admin (dashboard).

They share services and the database but are served on separate ports, and
admin routes are never mounted on the public app.
"""

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import health
from app.config import Settings

NO_STORE = {"Cache-Control": "no-store"}


def _base_app(settings: Settings) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.include_router(health.router)
    return app


def create_public_app(settings: Settings) -> FastAPI:
    app = _base_app(settings)
    root_page = settings.static_dir / "index.html"
    assets_dir = settings.static_dir / "assets"

    @app.get("/")
    def root() -> FileResponse:
        return FileResponse(root_page, headers=NO_STORE)

    # The build only emits an assets directory once a page has scripts or media.
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    return app


def create_admin_app(settings: Settings) -> FastAPI:
    return _base_app(settings)
