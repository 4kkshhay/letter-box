"""Response hardening and coarse request-size enforcement for both apps."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from app.config import Settings

MAX_REQUEST_BODY_BYTES = 64 * 1024

CONTENT_SECURITY_POLICY = "; ".join(
    (
        "default-src 'self'",
        "base-uri 'none'",
        "connect-src 'self'",
        "font-src 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
        "img-src 'self' data:",
        "media-src 'self'",
        "object-src 'none'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
    )
)

SECURITY_HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "Permissions-Policy": "camera=(), geolocation=(), microphone=(), payment=(), usb=()",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-Robots-Tag": "noindex, nofollow",
}


def install_security_middleware(
    app: FastAPI, settings: Settings, *, referrer_policy: str = "no-referrer"
) -> None:
    """Install last so every route, redirect and error receives the headers.

    Under `no-referrer`, browsers send `Origin: null` on HTML form posts, which
    the same-origin check rejects. The admin app's forms need `same-origin`.
    """

    @app.middleware("http")
    async def harden(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method in {"POST", "PUT", "PATCH"}:
            raw_length = request.headers.get("content-length")
            if raw_length:
                try:
                    length = int(raw_length)
                except ValueError:
                    response: Response = JSONResponse(
                        {"detail": "Invalid Content-Length"}, status_code=400
                    )
                else:
                    if length < 0:
                        response = JSONResponse(
                            {"detail": "Invalid Content-Length"}, status_code=400
                        )
                    elif length > MAX_REQUEST_BODY_BYTES:
                        response = JSONResponse(
                            {"detail": "Request body too large"}, status_code=413
                        )
                    else:
                        response = await call_next(request)
            else:
                response = await call_next(request)
        else:
            response = await call_next(request)

        for name, value in SECURITY_HEADERS.items():
            response.headers[name] = value
        # A route may ask for a different policy (the page gate's form does).
        response.headers.setdefault("Referrer-Policy", referrer_policy)
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        if request.url.path.startswith("/assets/") and response.status_code == 200:
            # Private: a shared cache (Cloudflare) must never serve page assets
            # to someone who has not unlocked a page.
            response.headers["Cache-Control"] = "private, max-age=31536000, immutable"
        elif request.url.path.startswith("/gate/") and response.status_code == 200:
            response.headers["Cache-Control"] = "public, max-age=86400"
        else:
            response.headers["Cache-Control"] = "no-store"
        return response
