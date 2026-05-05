"""Pydantic schemas crossing the HTTP boundary.

Everything inbound is validated by one of these models; the handlers
never see a raw `dict`. That keeps the validation cost paid once at
the edge."""
from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


# RFC 1035-ish FQDN regex — long enough to be useful, short enough to
# read. Rejects anything with whitespace, control chars, or shell
# metacharacters; all of which would suggest abuse rather than a real
# target.
_FQDN_RE = re.compile(
    r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$",
    re.IGNORECASE,
)


class ScanProfile(str, Enum):
    QUICK = "quick"
    DEEP = "deep"


class ScanStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    ERRORED = "errored"


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class ScanCreate(BaseModel):
    target: str = Field(min_length=4, max_length=253)
    profile: ScanProfile = ScanProfile.QUICK

    @field_validator("target")
    @classmethod
    def _looks_like_a_domain(cls, v: str) -> str:
        v = v.strip().lower()
        if not _FQDN_RE.match(v):
            raise ValueError("target must be a public domain (FQDN)")
        return v


class ScanResource(BaseModel):
    scan_id: str
    target: str
    profile: ScanProfile
    status: ScanStatus
    created_at: datetime
    finished_at: datetime | None = None


class ErrorBody(BaseModel):
    """Stable error contract — clients match on `code`."""
    code: str
    message: str


class ErrorEnvelope(BaseModel):
    error: ErrorBody


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    app: str
    version: str
