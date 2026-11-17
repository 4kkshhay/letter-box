"""Builds the two ASGI apps: public (pages) and admin (dashboard).

They share services and the database but are served on separate ports, and
admin routes are never mounted on the public app.
"""

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import health, public
from app.api.public import NO_STORE, redirect_to_root
from app.config import Settings
from app.services.pages import PageRegistry


def _base_app(settings: Settings, pages: PageRegistry) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, redirect_slashes=False)
    app.state.settings = settings
    app.state.pages = pages
    app.include_router(health.router)
    return app


def create_public_app(settings: Settings, pages: PageRegistry) -> FastAPI:
    app = _base_app(settings, pages)
    app.include_router(public.router)
    root_page = settings.static_dir / "index.html"
    assets_dir = settings.static_dir / "assets"

    @app.api_route("/", methods=["GET", "HEAD"])
    def root() -> FileResponse:
        return FileResponse(root_page, headers=NO_STORE)

    # The build only emits an assets directory once a page has scripts or media.
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.exception_handler(StarletteHTTPException)
    async def not_found(request: Request, exc: StarletteHTTPException) -> Response:
        """Anything unknown looks the same: a redirect to the neutral root page."""
        is_page_request = request.method in ("GET", "HEAD") and not request.url.path.startswith(
            "/api/"
        )
        if exc.status_code == 404 and is_page_request:
            return redirect_to_root()
        return await http_exception_handler(request, exc)

    return app


def create_admin_app(settings: Settings, pages: PageRegistry) -> FastAPI:
    return _base_app(settings, pages)
