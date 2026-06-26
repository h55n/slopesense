"""Redis cache dependency with JSON helpers."""

import json
import logging
from typing import Optional

from backend.config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Small JSON cache wrapper used by API endpoints."""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def get(self, key: str) -> Optional[dict]:
        value = await self.redis.get(key)
        return json.loads(value) if value else None

    async def set(self, key: str, value: dict, ttl_seconds: int = 300):
        await self.redis.setex(key, ttl_seconds, json.dumps(value, default=str))

    async def invalidate_pattern(self, pattern: str):
        async for key in self.redis.scan_iter(pattern):
            await self.redis.delete(key)


class MemoryCache:
    """Test/development fallback when Redis is unavailable."""

    def __init__(self):
        self.values = {}

    async def get(self, key: str) -> Optional[dict]:
        return self.values.get(key)

    async def set(self, key: str, value: dict, ttl_seconds: int = 300):
        self.values[key] = value

    async def invalidate_pattern(self, pattern: str):
        prefix = pattern.rstrip("*")
        for key in list(self.values):
            if key.startswith(prefix):
                self.values.pop(key, None)


_cache = None


async def get_cache():
    """Return a Redis-backed cache, falling back to in-memory cache."""
    global _cache
    if _cache is not None:
        return _cache
    try:
        import redis.asyncio as redis

        client = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        await client.ping()
        _cache = RedisCache(client)
    except Exception as exc:
        logger.warning("Using in-memory cache fallback: %s", exc)
        _cache = MemoryCache()
    return _cache
