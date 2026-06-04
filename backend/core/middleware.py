import uuid

import structlog
from itsdangerous import BadSignature, URLSafeTimedSerializer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from core.config import settings

logger = structlog.get_logger()

SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self'"
    ),
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}

CSRF_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: object) -> Response:
        correlation_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        request.state.correlation_id = correlation_id
        response: Response = await call_next(request)  # type: ignore[operator]
        response.headers["X-Correlation-Id"] = correlation_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: object) -> Response:
        response: Response = await call_next(request)  # type: ignore[operator]
        for key, value in SECURITY_HEADERS.items():
            response.headers[key] = value
        return response


class CSRFMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._serializer = URLSafeTimedSerializer(
            settings.csrf_secret_key.get_secret_value()
        )

    async def dispatch(self, request: Request, call_next: object) -> Response:
        if request.method in CSRF_SAFE_METHODS:
            return await call_next(request)  # type: ignore[operator,return-value]

        csrf_cookie = request.cookies.get("csrf_token")
        csrf_header = request.headers.get("X-CSRF-Token")

        if not csrf_cookie or not csrf_header:
            return JSONResponse({"error": "CSRF token missing"}, status_code=403)

        try:
            self._serializer.loads(csrf_cookie, max_age=86400)
        except BadSignature:
            return JSONResponse({"error": "Invalid CSRF token"}, status_code=403)

        if csrf_cookie != csrf_header:
            return JSONResponse({"error": "CSRF token mismatch"}, status_code=403)

        return await call_next(request)  # type: ignore[operator,return-value]
