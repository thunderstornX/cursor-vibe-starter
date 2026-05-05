"""Scan submission + retrieval.

The scan-running itself is intentionally elided: in the demo, scans
are stamped `done` immediately. This file is about HTTP-level
correctness — auth, validation, idempotent retrieval — not the
underlying scanner. See `prompts/01_api_design.md` for what a real
async-worker version would look like."""
from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status

from auth import JwtPayload, current_user
from models import ScanCreate, ScanResource
from redis_dep import get_redis
from scan_store import create_scan, get_scan, list_user_scans


router = APIRouter(prefix="/v1/scans", tags=["scans"])


@router.post("", response_model=ScanResource, status_code=status.HTTP_201_CREATED)
async def submit_scan(
    payload: ScanCreate,
    user: Annotated[JwtPayload, Depends(current_user)],
    redis=Depends(get_redis),
) -> ScanResource:
    return create_scan(redis, user=user.sub, payload=payload)


@router.get("/{scan_id}", response_model=ScanResource,
             responses={404: {"description": "scan not found"}})
async def get_one(
    scan_id: str,
    user: Annotated[JwtPayload, Depends(current_user)],
    redis=Depends(get_redis),
) -> ScanResource:
    record = get_scan(redis, user=user.sub, scan_id=scan_id)
    if record is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={"code": "scan.not_found", "message": "no such scan"},
        )
    return record


@router.get("", response_model=List[ScanResource])
async def list_mine(
    user: Annotated[JwtPayload, Depends(current_user)],
    redis=Depends(get_redis),
) -> list[ScanResource]:
    return list(list_user_scans(redis, user=user.sub))
