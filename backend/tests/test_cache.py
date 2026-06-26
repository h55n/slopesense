"""Tests for cache helpers."""

import pytest


@pytest.mark.asyncio
async def test_memory_cache_store_get_and_invalidate():
    from backend.api.cache import MemoryCache

    cache = MemoryCache()
    assert await cache.get("missing") is None

    await cache.set("district:WYD", {"fpi": 0.73})
    assert await cache.get("district:WYD") == {"fpi": 0.73}

    await cache.invalidate_pattern("district:*")
    assert await cache.get("district:WYD") is None
