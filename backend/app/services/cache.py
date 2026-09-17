"""
Redis client + simple JSON cache helpers, used to cache:
  - per-user recommendation lists (expensive to recompute on every request)
  - trending content rankings
"""
import json
from functools import lru_cache

import redis

from app.core.config import get_settings

settings = get_settings()


@lru_cache
def get_redis_client() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def cache_get_json(key: str):
    try:
        raw = get_redis_client().get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None  # cache miss / Redis down -> caller recomputes


def cache_set_json(key: str, value, ttl_seconds: int | None = None) -> None:
    try:
        client = get_redis_client()
        client.set(key, json.dumps(value), ex=ttl_seconds)
    except Exception:
        pass  # caching is a performance optimization, never a hard dependency


def cache_invalidate(key: str) -> None:
    try:
        get_redis_client().delete(key)
    except Exception:
        pass


def cache_invalidate_prefix(prefix: str) -> None:
    """Deletes all keys matching `prefix*` -- used when a single mutation
    (e.g. a new rating) could invalidate several cached variants at once
    (different top_k values, different rail types, etc)."""
    try:
        client = get_redis_client()
        for key in client.scan_iter(match=f"{prefix}*"):
            client.delete(key)
    except Exception:
        pass
