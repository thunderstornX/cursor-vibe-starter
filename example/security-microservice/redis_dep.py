"""Redis dependency.

Wrapped in a function so tests can override it via FastAPI's
`app.dependency_overrides`. Runtime calls fall through to a real
redis-py client; tests get fakeredis. No conditional imports inside
handlers — that's a smell."""
from __future__ import annotations

import redis as _redis

from config import Settings, get_settings

_client: _redis.Redis | None = None


def get_redis() -> _redis.Redis:
    global _client
    if _client is None:
        s: Settings = get_settings()
        _client = _redis.Redis.from_url(s.redis_url)
    return _client
