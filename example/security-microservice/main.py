"""FastAPI security microservice — the worked example.

This is a demo. It does *not* run real security scans. It exists to
show the shape of a clean, AI-pair-coded service: typed config that
refuses to start with a placeholder secret, JWT auth that fails the
right way under alg-confusion attempts, Redis rate limiting, JSON
access logs with secret redaction, structured error responses.

If you came here looking for a scanner, see `agentic-osint-agent` or
`llm-red-team-toolkit` in the same portfolio."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from auth import seed_demo_users
from config import get_settings
from logging_config import configure_logging
from middleware.rate_limiter import RateLimiterMiddleware
from middleware.request_logger import RequestLoggerMiddleware
from routes import auth as auth_routes
from routes import health as health_routes
from routes import scan as scan_routes


_BANNER = (
    "================================================================\n"
    "  cursor-vibe-starter :: security-microservice\n"
    "  FastAPI  ·  JWT  ·  Redis rate-limit  ·  v1.0\n"
    "  AMB · ORCID 0009-0007-2787-943X · 2026\n"
    "================================================================"
)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(level=settings.log_level)
    log = logging.getLogger("app.boot")

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # noqa: ARG001
        seed_demo_users(secret=settings.jwt_secret)
        for line in _BANNER.splitlines():
            log.info(line)
        log.info("service ready", extra={"port": settings.port})
        yield

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Middleware order matters: outermost runs first on the way in,
    # last on the way out. Rate-limit comes BEFORE request logging so
    # 429s are still observed; request-id propagation has to wrap
    # everything.
    app.add_middleware(RateLimiterMiddleware, settings=settings)
    app.add_middleware(RequestLoggerMiddleware)

    app.include_router(health_routes.router)
    app.include_router(auth_routes.router)
    app.include_router(scan_routes.router)

    @app.exception_handler(StarletteHTTPException)
    async def _http_handler(request: Request, exc: StarletteHTTPException):
        # FastAPI's default leaks the raw `detail` field. We coerce it
        # into our stable {"error": {"code", "message"}} shape so
        # clients get one contract.
        detail = exc.detail
        if isinstance(detail, dict) and "code" in detail and "message" in detail:
            body = {"error": detail}
        else:
            body = {"error": {"code": f"http.{exc.status_code}",
                               "message": str(detail) if detail else ""}}
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request,
                                    exc: RequestValidationError):
        # 422 with a stable code; the per-field detail is the LIST
        # FastAPI gave us, but with the request body redacted out so
        # we don't echo whatever the caller sent (it might contain
        # the password).
        return JSONResponse(
            status_code=422,
            content={"error": {
                "code": "request.invalid",
                "message": "request body did not pass validation",
            }},
        )

    return app


app = create_app()
