"""Public routes: page HTML by secret link, and the page bootstrap API."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response

from app.services.pages import Page
from app.services.state import read_state

NO_STORE = {"Cache-Control": "no-store"}

router = APIRouter()


def redirect_to_root() -> RedirectResponse:
    return RedirectResponse("/", status_code=302, headers=NO_STORE)


def _page_for(request: Request, slug: str) -> Page | None:
    return request.app.state.pages.by_slug(slug)


@router.api_route("/l/{slug}", methods=["GET", "HEAD"])
def page_html(slug: str, request: Request) -> Response:
    page = _page_for(request, slug)
    if page is None:
        return redirect_to_root()
    return FileResponse(page.html_path, headers=NO_STORE)


@router.get("/api/v1/pages/{slug}")
def page_bootstrap(slug: str, request: Request) -> JSONResponse:
    page = _page_for(request, slug)
    if page is None:
        # Same body as an unmatched route, so nothing distinguishes the two.
        raise HTTPException(status_code=404, detail="Not Found")
    state = read_state(request.app.state.settings.database_path, page)
    body: dict[str, Any] = {
        "title": page.config.title,
        "acknowledgement": page.config.acknowledgement,
        "fields": {name: field.model_dump() for name, field in page.config.fields.items()},
        "state": state.values,
        "acknowledged": state.acknowledged,
    }
    return JSONResponse(body, headers=NO_STORE)
