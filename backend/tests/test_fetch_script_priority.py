"""Persistence-backed fairness checks. No provider or production DB calls."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from backend.api.database import AsyncSessionLocal
from backend.models import SourceObservation
from scripts import fetch_source_observations as script


@pytest.mark.asyncio
async def test_oldest_first_missing_then_oldest_and_stable_ties():
    now = datetime.now(timezone.utc)
    points = [(code, code, 10.0, 70.0) for code in ["new", "old", "tie", "missing"]]
    async with AsyncSessionLocal() as db:
        for code, age in [("new", 1), ("old", 3), ("tie", 3), ("old", 9)]:
            db.add(
                SourceObservation(
                    point_code=code,
                    point_name=code,
                    lat=10,
                    lon=70,
                    source="test",
                    source_url="https://example.test",
                    fetched_at=now - timedelta(hours=age),
                    payload={},
                )
            )
        await db.commit()
    ordered = await script.oldest_first(points)
    assert [point[0] for point in ordered] == ["missing", "old", "tie", "new"]


@pytest.mark.asyncio
async def test_budget_limited_runs_do_not_starve_trailing_points(monkeypatch):
    points = [(f"P{i}", f"Point {i}", 10.0 + i, 70.0) for i in range(6)]
    monkeypatch.setattr(script, "POINTS", points)
    monkeypatch.setattr(script, "TIME_BUDGET_SECONDS", 2.5)
    clock = [0.0]
    calls, sleeps = [], []
    monkeypatch.setattr(script.time, "monotonic", lambda: clock[0])

    async def paced_sleep(delay):
        sleeps.append(delay)

    monkeypatch.setattr(script.asyncio, "sleep", paced_sleep)

    def fetch(lat, lon, now):
        calls.append(f"P{round(lat - 10)}")
        clock[0] += 1
        return "https://example.test", {"summary": {}}

    monkeypatch.setattr(script, "fetch_point", fetch)

    class KeepTestDatabase:
        async def dispose(self):
            pass

    monkeypatch.setattr(script, "engine", KeepTestDatabase())
    await script.run()
    assert calls == ["P0", "P1", "P2"]
    clock[0] = 0.0
    await script.run()
    assert calls == ["P0", "P1", "P2", "P3", "P4", "P5"]
    assert len(sleeps) == 4
    assert all(7 <= delay <= 9 for delay in sleeps)
    async with AsyncSessionLocal() as db:
        codes = (await db.execute(select(SourceObservation.point_code))).scalars().all()
    assert sorted(codes) == [f"P{i}" for i in range(6)]


@pytest.mark.asyncio
async def test_empty_registry_returns_empty():
    assert await script.oldest_first([]) == []


@pytest.mark.asyncio
async def test_below_threshold_refresh_commits_only_successes_and_keeps_old_values(
    monkeypatch,
):
    points = [(f"P{i}", f"Point {i}", 10.0 + i, 70.0) for i in range(6)]
    old = datetime.now(timezone.utc) - timedelta(hours=8)
    async with AsyncSessionLocal() as db:
        for code, name, lat, lon in points:
            db.add(
                SourceObservation(
                    point_code=code,
                    point_name=name,
                    lat=lat,
                    lon=lon,
                    source="test",
                    source_url="https://example.test",
                    fetched_at=old,
                    payload={"old": True},
                )
            )
        await db.commit()
    monkeypatch.setattr(script, "POINTS", points)
    monkeypatch.setattr(script, "TIME_BUDGET_SECONDS", 1.5)
    clock, sleeps = [0.0], []
    monkeypatch.setattr(script.time, "monotonic", lambda: clock[0])

    async def paced_sleep(delay):
        sleeps.append(delay)

    monkeypatch.setattr(script.asyncio, "sleep", paced_sleep)

    def fetch(lat, lon, now):
        clock[0] += 1
        return "https://example.test", {"new": True}

    monkeypatch.setattr(script, "fetch_point", fetch)

    class KeepTestDatabase:
        async def dispose(self):
            pass

    monkeypatch.setattr(script, "engine", KeepTestDatabase())
    with pytest.raises(SystemExit, match="successful snapshots persisted"):
        await script.run()
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(SourceObservation))).scalars().all()
    new = [row for row in rows if row.payload.get("new")]
    assert [row.point_code for row in new] == ["P0", "P1"]
    assert len(rows) == 8
    assert all(row.payload == {"old": True} for row in rows if row not in new)
    assert [point[0] for point in await script.oldest_first(points)] == [
        "P2",
        "P3",
        "P4",
        "P5",
        "P0",
        "P1",
    ]
    assert len(sleeps) == 1 and 7 <= sleeps[0] <= 9
