import asyncio

import pytest

from scripts import fetch_source_observations as script
from backend.ingestion.quality import DataUnavailableError


class FakeSession:
    def __init__(self, store):
        self.store = store

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def add_all(self, rows):
        self.store.extend(rows)

    async def execute(self, *_):
        return None

    async def commit(self):
        self.store.append("commit")


class FakeEngine:
    async def dispose(self):
        return None


def _setup(monkeypatch, failing):
    store = []

    async def registry_order(points):
        return list(points)

    monkeypatch.setattr(script, "oldest_first", registry_order)
    points = [(f"P{i}", f"Point {i}", 10.0 + i, 70.0) for i in range(6)]
    monkeypatch.setattr(script, "POINTS", points)
    monkeypatch.setattr(script, "AsyncSessionLocal", lambda: FakeSession(store))
    monkeypatch.setattr(script, "engine", FakeEngine())

    async def no_sleep(_):
        return None

    monkeypatch.setattr(script.asyncio, "sleep", no_sleep)

    def fake_fetch(lat, lon, now):
        if round(lat - 10.0) in failing:
            raise DataUnavailableError("throttled")
        return "https://example.test/x", {"summary": {}}

    monkeypatch.setattr(script, "fetch_point", fake_fetch)
    return store


def test_partial_failure_persists_the_successful_points(monkeypatch):
    store = _setup(monkeypatch, failing={1, 4})
    asyncio.run(script.run())
    rows = [r for r in store if r != "commit"]
    assert sorted(r.point_code for r in rows) == ["P0", "P2", "P3", "P5"]
    assert "commit" in store


def test_run_fails_when_most_points_fail(monkeypatch):
    store = _setup(monkeypatch, failing={0, 1, 2, 3})
    with pytest.raises(SystemExit):
        asyncio.run(script.run())
    assert store == []


def test_stops_after_consecutive_failures(monkeypatch):
    _setup(monkeypatch, failing={0, 1, 2, 3, 4, 5})
    calls = []
    orig = script.fetch_point

    def counting(lat, lon, now):
        calls.append(lat)
        return orig(lat, lon, now)

    monkeypatch.setattr(script, "fetch_point", counting)
    with pytest.raises(SystemExit):
        asyncio.run(script.run())
    assert len(calls) == script.MAX_CONSECUTIVE_FAILURES
