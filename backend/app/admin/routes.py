"""Authenticated admin routes: dashboard, preview, reset and QR downloads."""

from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs

import segno
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app.admin.auth import (
    SESSION_COOKIE,
    SESSION_LIFETIME_SECONDS,
    LoginThrottle,
    create_session,
    valid_session,
    verify_password,
)
from app.admin.services import (
    admin_page_payload,
    page_detail,
    page_summaries,
    public_page_url,
    reset_page,
)
from app.api.public import NO_STORE, require_same_origin
from app.services.pages import Page

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
throttle = LoginThrottle()


def _time(value: datetime) -> str:
    return value.strftime("%I:%M %p").lstrip("0").lower()


def _day(value: date) -> str:
    return f"{value.strftime('%a')} {value.day} {value.strftime('%b %Y')}"


def _when(value: datetime) -> str:
    return f"{_day(value.date())}, {_time(value)}"


templates.env.filters.update(time=_time, day=_day, when=_when)


def _page(request: Request, name: str) -> Page:
    page = request.app.state.pages.by_name(name)
    if page is None:
        raise HTTPException(status_code=404, detail="Not Found")
    return page


def _logged_in(request: Request) -> bool:
    settings = request.app.state.settings
    return valid_session(request.cookies.get(SESSION_COOKIE), settings.session_secret)


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request) -> Response:
    if _logged_in(request):
        return RedirectResponse("/", status_code=303, headers=NO_STORE)
    return templates.TemplateResponse(request, "login.html", {"error": None}, headers=NO_STORE)


@router.post("/login", response_class=HTMLResponse)
async def login(request: Request) -> Response:
    if not throttle.allowed():
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Too many attempts. Try again in a few minutes."},
            status_code=429,
            headers=NO_STORE,
        )
    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > 4096:
            raise HTTPException(status_code=413, detail="Request body too large")
    password = ""
    if content_type == "application/x-www-form-urlencoded":
        password = parse_qs(body.decode("utf-8", errors="replace")).get("password", [""])[0]
    settings = request.app.state.settings
    if not settings.admin_password_hash or not verify_password(password, settings.admin_password_hash):
        throttle.failed()
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Incorrect password."},
            status_code=401,
            headers=NO_STORE,
        )

    throttle.reset()
    response = RedirectResponse("/", status_code=303, headers=NO_STORE)
    response.set_cookie(
        SESSION_COOKIE,
        create_session(settings.session_secret),
        max_age=SESSION_LIFETIME_SECONDS,
        httponly=True,
        secure=settings.is_production,
        samesite="strict",
        path="/",
    )
    return response


@router.post("/logout")
def logout(request: Request) -> RedirectResponse:
    require_same_origin(request)
    response = RedirectResponse("/login", status_code=303, headers=NO_STORE)
    response.delete_cookie(
        SESSION_COOKIE,
        httponly=True,
        secure=request.app.state.settings.is_production,
        samesite="strict",
        path="/",
    )
    return response


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> Response:
    settings = request.app.state.settings
    pages = page_summaries(settings.database_path, request.app.state.pages, request.app.state.tz)
    return templates.TemplateResponse(
        request, "dashboard.html", {"pages": pages}, headers=NO_STORE
    )


@router.get("/pages/{name}", response_class=HTMLResponse)
def page_stats(name: str, request: Request) -> Response:
    settings = request.app.state.settings
    try:
        detail = page_detail(
            settings.database_path,
            _page(request, name),
            settings.public_base_url,
            request.app.state.tz,
            production=settings.is_production,
        )
    except ValueError as error:
        raise HTTPException(status_code=503, detail=str(error)) from None
    return templates.TemplateResponse(
        request, "page.html", {"detail": detail}, headers=NO_STORE
    )


@router.get("/view/{name}")
def view_page(name: str, request: Request) -> FileResponse:
    return FileResponse(_page(request, name).html_path, headers=NO_STORE)


@router.get("/api/v1/pages/{name}")
def page_bootstrap(name: str, request: Request) -> JSONResponse:
    page = _page(request, name)
    return JSONResponse(
        admin_page_payload(request.app.state.settings.database_path, page), headers=NO_STORE
    )


@router.post("/pages/{name}/reset")
def reset(name: str, request: Request) -> RedirectResponse:
    require_same_origin(request)
    reset_page(request.app.state.settings.database_path, _page(request, name))
    return RedirectResponse(f"/pages/{name}", status_code=303, headers=NO_STORE)


def _qr_response(name: str, request: Request, kind: str) -> Response:
    page = _page(request, name)
    settings = request.app.state.settings
    try:
        url = public_page_url(settings.public_base_url, page, production=settings.is_production)
    except ValueError as error:
        raise HTTPException(status_code=503, detail=str(error)) from None
    qr = segno.make_qr(url, error="h")
    output = BytesIO()
    if kind == "png":
        qr.save(output, kind="png", scale=8, border=4, dark="#000", light="#fff")
        media_type = "image/png"
    else:
        qr.save(output, kind="svg", scale=8, border=4, dark="#000", light="#fff", xmldecl=False)
        media_type = "image/svg+xml"
    return Response(
        output.getvalue(),
        media_type=media_type,
        headers={
            **NO_STORE,
            "Content-Disposition": f'attachment; filename="{page.name}-qr.{kind}"',
        },
    )


@router.get("/pages/{name}/qr.png")
def qr_png(name: str, request: Request) -> Response:
    return _qr_response(name, request, "png")


@router.get("/pages/{name}/qr.svg")
def qr_svg(name: str, request: Request) -> Response:
    return _qr_response(name, request, "svg")
