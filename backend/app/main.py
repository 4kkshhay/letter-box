"""Builds the two ASGI apps: public (pages) and admin (dashboard).

They share services and the database but are served on separate ports, and
admin routes are never mounted on the public app.
"""

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.admin import routes as admin
from app.admin.auth import SESSION_COOKIE, password_hash_configured, valid_session
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
    if not password_hash_configured(settings.admin_password_hash):
        raise RuntimeError("ADMIN_PASSWORD_HASH is missing or invalid")
    if not settings.session_secret:
        raise RuntimeError("SESSION_SECRET is missing")
    if settings.is_production and len(settings.session_secret) < 32:
        raise RuntimeError("SESSION_SECRET must be at least 32 characters in production")
    app = _base_app(settings, pages)
    assets_dir = settings.static_dir / "assets"

    @app.middleware("http")
    async def require_admin_session(request: Request, call_next):
        public_paths = {"/login", "/health", "/health/ready"}
        if request.url.path not in public_paths and not valid_session(
            request.cookies.get(SESSION_COOKIE), settings.session_secret
        ):
            if request.url.path.startswith("/api/"):
                return Response(
                    '{"detail":"Unauthorized"}',
                    status_code=401,
                    media_type="application/json",
                    headers=NO_STORE,
                )
            return redirect_to_login()
        return await call_next(request)

    app.include_router(admin.router)
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="admin-assets")
    return app


def redirect_to_login() -> Response:
    from fastapi.responses import RedirectResponse

    return RedirectResponse("/login", status_code=303, headers=NO_STORE)
