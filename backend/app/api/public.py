"""Public routes: page HTML by link, and the page API."""

import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

from app.gate import (
    HINT_AFTER_FAILURES,
    MAX_PASSWORD_CHARS,
    PAGE_UNLOCK_SECONDS,
    RESOURCE_UNLOCK_SECONDS,
    UNLOCK_COOKIE,
    GateThrottle,
    create_unlock,
    password_matches,
    unlocked,
)
from app.services.pages import Page
from app.services.state import (
    OPEN_KINDS,
    InvalidFields,
    OpenLocation,
    page_was_opened,
    visitor_timezone,
    read_state,
    record_open,
    save_fields,
    validate_fields,
)

NO_STORE = {"Cache-Control": "no-store"}
MAX_BODY_BYTES = 64 * 1024

router = APIRouter()
gate_templates = Jinja2Templates(directory=Path(__file__).parent.parent / "gate" / "templates")
gate_throttle = GateThrottle()


def redirect_to_root() -> RedirectResponse:
    return RedirectResponse("/", status_code=302, headers=NO_STORE)


def _page_for(request: Request, slug: str) -> Page | None:
    return request.app.state.pages.by_slug(slug)


def gate_enabled(request: Request) -> bool:
    return bool(request.app.state.settings.page_password_hashes)


def has_unlock(request: Request, page: Page | None, max_age: int) -> bool:
    """Whether the gate lets this request through; always when the gate is off."""
    if not gate_enabled(request):
        return True
    return unlocked(
        request.cookies.get(UNLOCK_COOKIE),
        request.app.state.settings.session_secret,
        page_name=page.name if page else None,
        max_age=max_age,
    )


def _require_page(request: Request, slug: str) -> Page:
    page = _page_for(request, slug)
    if page is None or not has_unlock(request, page, RESOURCE_UNLOCK_SECONDS):
        # Same body as an unmatched route, so nothing distinguishes the two.
        raise HTTPException(status_code=404, detail="Not Found")
    return page


def require_same_origin(request: Request) -> None:
    """Mutations must come from a page served by this site.

    Browsers always send Origin on these requests and scripts cannot forge it.
    """
    origin = request.headers.get("origin")
    host = request.headers.get("host")
    if not origin or not host or urlsplit(origin).netloc != host:
        raise HTTPException(status_code=403, detail="Forbidden")


async def _read_json_body(request: Request) -> Any:
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type != "application/json":
        raise HTTPException(status_code=415, detail="Expected application/json")
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_BODY_BYTES:
            raise HTTPException(status_code=413, detail="Request body too large")
    try:
        return json.loads(body)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid input") from None


def _location_header(request: Request, name: str) -> str | None:
    """A Cloudflare visitor location header as clean text, or None.

    The origin is reachable only through the tunnel, and Cloudflare sets these
    headers at its edge. They are approximate and IP-derived; they are shown to
    the admin as a hint and never used for decisions.
    """
    raw = request.headers.get(name)
    if raw is None:
        return None
    try:
        # HTTP headers arrive as latin-1; Cloudflare sends UTF-8 place names.
        value = raw.encode("latin-1").decode("utf-8")
    except UnicodeError:
        value = raw
    value = "".join(ch for ch in value if ch.isprintable()).strip()[:100]
    return value or None


def _open_location(request: Request) -> OpenLocation:
    country = _location_header(request, "cf-ipcountry")
    if country in {"XX", "T1"}:  # Cloudflare's codes for unknown and Tor
        country = None
    return OpenLocation(
        city=_location_header(request, "cf-ipcity"),
        region=_location_header(request, "cf-region"),
        country=country,
    )


def _visitor(request: Request) -> str:
    # The origin is reachable only through the tunnel, which sets this header.
    return request.headers.get("cf-connecting-ip") or (request.client.host if request.client else "")


def _gate(request: Request, *, status_code: int = 200, message: str = "", hint: bool = False) -> Response:
    recipient = request.app.state.recipient
    return gate_templates.TemplateResponse(
        request,
        "gate.html",
        {
            "name": recipient.name,
            "message": message,
            "hint": recipient.hint if hint else "",
            "attempted": request.method == "POST",
        },
        status_code=status_code,
        # Form posts from a `no-referrer` page carry `Origin: null`, which the
        # same-origin check rejects; this page's own address is never sent off-site.
        headers={**NO_STORE, "Referrer-Policy": "same-origin", "X-Page-Gate": "locked"},
    )


@router.api_route("/l/{slug}", methods=["GET", "HEAD"])
def legacy_page_link(slug: str, request: Request) -> Response:
    """Links used to live under /l/; send any older ones to the page's address."""
    if _page_for(request, slug) is None:
        return redirect_to_root()
    return RedirectResponse(f"/{slug}", status_code=302, headers=NO_STORE)


# Single path segments only. Slugs are at least 10 characters, so they can
# never equal a fixed route such as /health, /api, /assets or /gate.
@router.api_route("/{slug}", methods=["GET", "HEAD"])
def page_html(slug: str, request: Request) -> Response:
    page = _page_for(request, slug)
    if page is None:
        return redirect_to_root()
    if not has_unlock(request, page, PAGE_UNLOCK_SECONDS):
        return _gate(request)
    return FileResponse(page.html_path, headers=NO_STORE)


@router.post("/{slug}")
async def unlock_page(slug: str, request: Request) -> Response:
    """Check the gate password; on success, unlock this page and show it."""
    page = _page_for(request, slug)
    if page is None:
        return redirect_to_root()
    if not gate_enabled(request):
        return RedirectResponse(request.url.path, status_code=303, headers=NO_STORE)
    require_same_origin(request)
    settings = request.app.state.settings
    visitor = _visitor(request)
    # Generous until the page is first opened, so working out the password
    # never locks its first visitor out.
    tight = await run_in_threadpool(page_was_opened, settings.database_path, page)
    if not gate_throttle.allowed(visitor, tight=tight):
        return _gate(
            request,
            status_code=429,
            message="Let's pause for a moment. Try again in a little while.",
            hint=True,
        )

    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > 4096:
            raise HTTPException(status_code=413, detail="Request body too large")
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    password = ""
    if content_type == "application/x-www-form-urlencoded":
        password = parse_qs(body.decode("utf-8", errors="replace")).get("password", [""])[0]
    password = password[:MAX_PASSWORD_CHARS]

    if not await run_in_threadpool(password_matches, password, settings.page_password_hashes):
        if password.strip():
            gate_throttle.failed(visitor)
        failures = gate_throttle.failures(visitor)
        return _gate(
            request,
            status_code=401,
            message="Not quite. Try once more.",
            hint=failures >= HINT_AFTER_FAILURES,
        )

    gate_throttle.succeeded(visitor)
    response = RedirectResponse(request.url.path, status_code=303, headers=NO_STORE)
    response.set_cookie(
        UNLOCK_COOKIE,
        create_unlock(settings.session_secret, page.name),
        max_age=RESOURCE_UNLOCK_SECONDS,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )
    return response


@router.get("/api/v1/pages/{slug}")
def page_bootstrap(slug: str, request: Request) -> JSONResponse:
    page = _require_page(request, slug)
    body: dict[str, Any] = {
        "title": page.config.title,
        "fields": {name: field.model_dump() for name, field in page.config.fields.items()},
        "state": read_state(request.app.state.settings.database_path, page),
    }
    return JSONResponse(body, headers=NO_STORE)


@router.patch("/api/v1/pages/{slug}/state", dependencies=[Depends(require_same_origin)])
async def save_page_state(slug: str, request: Request) -> JSONResponse:
    page = _require_page(request, slug)
    body = await _read_json_body(request)
    if not isinstance(body, dict) or set(body) != {"fields"} or not isinstance(body["fields"], dict):
        raise HTTPException(status_code=422, detail="Invalid input")
    try:
        fields = validate_fields(page, body["fields"])
    except InvalidFields as error:
        return JSONResponse(
            {"detail": "Invalid input", "errors": error.errors}, status_code=422, headers=NO_STORE
        )
    database_path = request.app.state.settings.database_path
    tz = visitor_timezone(request.query_params.get("tz"))
    state = await run_in_threadpool(save_fields, database_path, page, fields, tz)
    return JSONResponse({"state": state, "saved": True}, headers=NO_STORE)


@router.post("/api/v1/pages/{slug}/open", dependencies=[Depends(require_same_origin)])
def record_page_open(slug: str, request: Request) -> Response:
    """The first recorded open is what the dashboard shows as "received".

    `?kind=` is the browser's navigation type; without it the open is stored
    with an unknown kind. `?tz=` is the visitor's IANA timezone; an unknown
    value is ignored rather than failing the open.
    """
    page = _require_page(request, slug)
    kind = request.query_params.get("kind")
    if kind is not None and kind not in OPEN_KINDS:
        raise HTTPException(status_code=422, detail="Invalid input")
    record_open(
        request.app.state.settings.database_path,
        page,
        kind,
        _open_location(request),
        visitor_timezone(request.query_params.get("tz")),
    )
    return Response(status_code=204, headers=NO_STORE)
