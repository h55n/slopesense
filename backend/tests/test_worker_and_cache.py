"""Coverage for cache helpers and worker orchestration."""

import asyncio
import sys
import types

import pytest


class FakeRedisClient:
    def __init__(self):
        self.values = {}
        self.deleted = []

    async def get(self, key):
        return self.values.get(key)

    async def setex(self, key, ttl_seconds, value):
        self.values[key] = value

    async def ping(self):
        return True

    async def delete(self, key):
        self.deleted.append(key)
        self.values.pop(key, None)

    async def scan_iter(self, pattern):
        prefix = pattern.rstrip("*")
        for key in list(self.values):
            if key.startswith(prefix):
                yield key


@pytest.mark.asyncio
async def test_redis_cache_round_trip_and_invalidate():
    from backend.api.cache import RedisCache

    cache = RedisCache(FakeRedisClient())
    await cache.set("alerts:KL", {"fpi": 0.73})
    assert await cache.get("alerts:KL") == {"fpi": 0.73}
    await cache.invalidate_pattern("alerts:*")
    assert await cache.get("alerts:KL") is None


@pytest.mark.asyncio
async def test_get_cache_returns_memory_cache_on_redis_failure(monkeypatch):
    import backend.api.cache as cache_mod

    cache_mod._cache = None
    monkeypatch.setitem(sys.modules, "redis.asyncio", None)
    cache = await cache_mod.get_cache()

    assert await cache.get("missing") is None


def test_worker_run_model_pipeline_success(monkeypatch):
    import backend.worker as worker

    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {"run_timestamp": "2026-06-24T00:00:00Z", "messages_sent": 3}

    def fake_post(url, params=None, timeout=None):
        assert url.endswith("/internal/trigger-run")
        return Response()

    fake_httpx = types.SimpleNamespace(post=fake_post)
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)

    result = worker.run_model_pipeline()
    assert result["messages_sent"] == 3


def test_worker_run_model_pipeline_failure(monkeypatch):
    import backend.worker as worker

    class DummySelf:
        def retry(self, exc=None, countdown=None):
            raise RuntimeError(f"retry:{countdown}")

    class Response:
        status_code = 500
        text = "boom"

    def fake_post(*args, **kwargs):
        return Response()

    fake_httpx = types.SimpleNamespace(post=fake_post)
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)
    monkeypatch.setattr(worker.run_model_pipeline, "retry", DummySelf().retry, raising=False)

    with pytest.raises(RuntimeError, match="retry:300"):
        worker.run_model_pipeline.__wrapped__()


def test_worker_one_off_tasks_and_scheduler(monkeypatch):
    import backend.worker as worker

    monkeypatch.setitem(sys.modules, "backend.model.retrospective", types.SimpleNamespace(
        RetrospectiveRunner=lambda: types.SimpleNamespace(run_all=lambda use_synthetic=True: {"flagged_at_t24": 6})
    ))

    assert worker.send_whatsapp_alert.run("a1", "c1") is None
    assert worker.send_daily_digest.run() is None
    assert worker.run_retrospective.run() == {"flagged_at_t24": 6}

    scheduler = worker.start_apscheduler()
    assert scheduler.get_jobs()
