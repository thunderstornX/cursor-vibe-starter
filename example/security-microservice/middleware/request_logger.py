"""Request-id + JSON access logger.

Generates (or honours) a request id, stashes it on a contextvar so
downstream code can grab it, and emits one INFO log per request with
latency and status. Headers are NEVER logged — they're the easiest
way to leak a JWT or an API key."""
from __future__ import annotations

import contextvars
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """One access log per request. JSON-formatted by the parent logger."""

    def __init__(self, app, *, logger_name: str = "app.access") -> None:
        super().__init__(app)
        self._logger = logging.getLogger(logger_name)

    async def dispatch(self, request: Request, call_next) -> Response:
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
        token = request_id_ctx.set(rid)
        started = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            latency_ms = int((time.monotonic() - started) * 1000)
            self._logger.exception(
                "request errored",
                extra={"request_id": rid,
                        "method": request.method,
                        "path": request.url.path,
                        "latency_ms": latency_ms,
                        "status": 500},
            )
            request_id_ctx.reset(token)
            raise

        latency_ms = int((time.monotonic() - started) * 1000)
        self._logger.info(
            "%s %s -> %d (%dms)",
            request.method, request.url.path, response.status_code, latency_ms,
            extra={"request_id": rid,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "latency_ms": latency_ms},
        )
        response.headers["X-Request-ID"] = rid
        request_id_ctx.reset(token)
        return response
