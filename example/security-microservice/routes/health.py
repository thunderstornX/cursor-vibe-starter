"""GET /health — cheap liveness probe.

Deliberately does NOT touch Redis; that's the readiness probe's job.
A liveness check that depends on a sidecar restart-loops the service
when the sidecar is the thing that's broken."""
from __future__ import annotations

from fastapi import APIRouter

from models import HealthResponse


router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["meta"])
async def health() -> HealthResponse:
    return HealthResponse(app="security-microservice", version="1.0.0")
