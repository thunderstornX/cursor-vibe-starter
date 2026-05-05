"""Tiny Redis-backed scan store.

Production version of this would be a Postgres table; for the demo we
keep everything in Redis hashes so the docker-compose stack stays
two services. Keys:

    scan:{user}:{id}   -> hash of scan fields
    user_scans:{user}  -> set of scan IDs for that user

The store does *not* run scans — it just records their state. A
worker would normally pop the queue; here we mark the scan `done`
synchronously so the demo behaves end-to-end without a background
process."""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Iterable, Protocol

from models import ScanCreate, ScanProfile, ScanResource, ScanStatus


class _RedisLike(Protocol):
    """Subset of redis.Redis we use; satisfied by both real Redis and
    fakeredis."""
    def hset(self, key: str, mapping: dict) -> int: ...  # type: ignore[no-untyped-def]
    def hgetall(self, key: str) -> dict: ...  # type: ignore[no-untyped-def]
    def sadd(self, key: str, *values: str) -> int: ...  # type: ignore[no-untyped-def]
    def smembers(self, key: str) -> set: ...  # type: ignore[no-untyped-def]
    def expire(self, key: str, seconds: int) -> int: ...  # type: ignore[no-untyped-def]


# Scans live for 24h in the demo. Long enough to play with, short
# enough not to wedge dev environments full of leftovers.
_TTL_SECONDS = 24 * 60 * 60


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _scan_key(user: str, scan_id: str) -> str:
    return f"scan:{user}:{scan_id}"


def _user_scans_key(user: str) -> str:
    return f"user_scans:{user}"


def _decode(value) -> str:
    """Redis returns bytes by default; fakeredis sometimes returns str.
    Normalise so handlers can stay agnostic."""
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def create_scan(redis: _RedisLike, *, user: str, payload: ScanCreate) -> ScanResource:
    scan_id = str(uuid.uuid4())
    now = _now()
    record = ScanResource(
        scan_id=scan_id,
        target=payload.target,
        profile=payload.profile,
        # In a real system this would be QUEUED while a worker picks
        # it up. The demo runs the "scan" inline: WHOIS-like checks
        # are out of scope for this repo, so we just stamp it done.
        status=ScanStatus.DONE,
        created_at=now,
        finished_at=now,
    )
    fields = {
        "scan_id": record.scan_id,
        "target": record.target,
        "profile": record.profile.value,
        "status": record.status.value,
        "created_at": record.created_at.isoformat(),
        "finished_at": record.finished_at.isoformat() if record.finished_at else "",
    }
    redis.hset(_scan_key(user, scan_id), mapping=fields)
    redis.expire(_scan_key(user, scan_id), _TTL_SECONDS)
    redis.sadd(_user_scans_key(user), scan_id)
    redis.expire(_user_scans_key(user), _TTL_SECONDS)
    return record


def get_scan(redis: _RedisLike, *, user: str, scan_id: str) -> ScanResource | None:
    raw = redis.hgetall(_scan_key(user, scan_id))
    if not raw:
        return None
    fields = {_decode(k): _decode(v) for k, v in raw.items()}
    return ScanResource(
        scan_id=fields["scan_id"],
        target=fields["target"],
        profile=ScanProfile(fields["profile"]),
        status=ScanStatus(fields["status"]),
        created_at=datetime.fromisoformat(fields["created_at"]),
        finished_at=(datetime.fromisoformat(fields["finished_at"])
                      if fields.get("finished_at") else None),
    )


def list_user_scans(redis: _RedisLike, *, user: str) -> Iterable[ScanResource]:
    members = redis.smembers(_user_scans_key(user))
    for raw_id in members:
        scan = get_scan(redis, user=user, scan_id=_decode(raw_id))
        if scan is not None:
            yield scan
