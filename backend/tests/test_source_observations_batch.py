"""Batched provider fetch and API inline refresh. No live provider calls."""

from datetime import datetime, timedelta, timezone
import json

import pytest
from sqlalchemy import select

from backend.api import observations as api_observations
from backend.api.database import AsyncSessionLocal
from backend.ingestion import source_observations as ingestion
from backend.ingestion.point_registry import POINT_BY_CODE
from backend.ingestion.quality import DataUnavailableError
from backend.models import SourceObservation
from scripts import fetch_source_observations as script

NOW = datetime.now(timezone.utc).replace(microsecond=0)


def _hourly_payload():
    # summarize() requires exact whole-hour UTC coverage around the cutoff hour.
    cutoff = NOW.replace(minute=0, second=0, microsecond=0)
    times = [
        (cutoff - timedelta(hours=72) + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M")
        for h in range(72 + 49)
    ]
    return {
        "latitude": 10.0,
        "longitude": 70.0,
        "elevation": 100.0,
        "hourly_units": {"rain": "mm"},
        "hourly": {
            "time": times,
            "rain": [0.1] * len(times),
            "soil_moisture_0_to_1cm": [0.3] * len(times),
        },
    }


class FakeResponse:
    def __init__(self, payload, status=200):
        self.status = status
        self._body = json.dumps(payload).encode()

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_batch_fetch_summarizes_every_point(monkeypatch):
    points = [("AAA", "A", 10.0, 70.0), ("BBB", "B", 11.0, 71.0)]
    seen = {}

    def fake_urlopen(url, timeout):
        seen["url"] = url
        return FakeResponse([_hourly_payload(), _hourly_payload()])

    monkeypatch.setattr(ingestion, "urlopen", fake_urlopen)
    url, results = ingestion.fetch_points_batch(points, NOW)
    assert "latitude=10.0%2C11.0" in url and "longitude=70.0%2C71.0" in url
    assert sorted(results) == ["AAA", "BBB"]
    summary = results["AAA"]["summary"]
    assert summary["modeled_large_scale_rain_previous_24h_mm"] == pytest.approx(2.4)
    assert summary["used_for_warnings"] is False


def test_batch_fetch_rejects_count_mismatch(monkeypatch):
    points = [("AAA", "A", 10.0, 70.0), ("BBB", "B", 11.0, 71.0)]
    monkeypatch.setattr(
        ingestion, "urlopen", lambda url, timeout: FakeResponse([_hourly_payload()])
    )
    with pytest.raises(DataUnavailableError, match="2 points"):
        ingestion.fetch_points_batch(points, NOW)


def test_batch_fetch_skips_only_the_invalid_point(monkeypatch):
    points = [("AAA", "A", 10.0, 70.0), ("BBB", "B", 11.0, 71.0)]
    bad = _hourly_payload()
    bad["hourly"]["rain"][100] = None  # inside the forecast window
    monkeypatch.setattr(
        ingestion,
        "urlopen",
        lambda url, timeout: FakeResponse([bad, _hourly_payload()]),
    )
    _url, results = ingestion.fetch_points_batch(points, NOW)
    assert sorted(results) == ["BBB"]


@pytest.mark.asyncio
async def test_script_batch_path_covers_all_points_without_pacing(monkeypatch):
    points = [(f"P{i}", f"Point {i}", 10.0 + i, 70.0) for i in range(6)]
    monkeypatch.setattr(script, "POINTS", points)

    async def registry_order(items):
        return list(items)

    monkeypatch.setattr(script, "oldest_first", registry_order)

    class KeepTestDatabase:
        async def dispose(self):
            pass

    monkeypatch.setattr(script, "engine", KeepTestDatabase())

    def batch(items, now):
        return "https://example.test/batch", {
            code: {"summary": {}} for code, _n, _la, _lo in items
        }

    monkeypatch.setattr(script, "fetch_points_batch", batch)

    def fail_point(lat, lon, now):
        raise AssertionError("per-point path must not run after a full batch")

    monkeypatch.setattr(script, "fetch_point", fail_point)

    await script.run()
    async with AsyncSessionLocal() as db:
        codes = (await db.execute(select(SourceObservation.point_code))).scalars().all()
    assert sorted(codes) == [f"P{i}" for i in range(6)]


@pytest.mark.asyncio
async def test_points_needing_refresh_flags_only_old_or_missing():
    now = datetime.now(timezone.utc)
    fresh = now - timedelta(minutes=5)
    old = now - timedelta(hours=2)
    sample = list(POINT_BY_CODE)
    latest = {code: fresh for code in sample}
    assert api_observations._points_needing_refresh(latest, now) == []
    latest[sample[0]] = old
    del latest[sample[1]]
    assert sorted(api_observations._points_needing_refresh(latest, now)) == sorted(
        [sample[0], sample[1]]
    )


@pytest.mark.asyncio
async def test_endpoint_refreshes_stale_points_inline(monkeypatch):
    old = datetime.now(timezone.utc) - timedelta(hours=8)
    async with AsyncSessionLocal() as db:
        for code, point in POINT_BY_CODE.items():
            db.add(
                SourceObservation(
                    point_code=code,
                    point_name=point["point_name"],
                    lat=point["latitude"],
                    lon=point["longitude"],
                    source="test",
                    source_url="https://example.test",
                    fetched_at=old,
                    payload={"summary": {"stale_marker": True}},
                )
            )
        await db.commit()

    refreshed = []

    def batch(points, now):
        refreshed.extend(code for code, _n, _la, _lo in points)
        return "https://example.test/batch", {
            code: {"summary": {"stale_marker": False}} for code, _n, _la, _lo in points
        }

    monkeypatch.setattr(
        "backend.ingestion.source_observations.fetch_points_batch", batch
    )

    async with AsyncSessionLocal() as db:
        result = await api_observations.latest_source_observations(db=db)

    assert sorted(refreshed) == sorted(POINT_BY_CODE)
    assert result["count"] == len(POINT_BY_CODE)
    assert result["missing_point_codes"] == []
    assert all(not obs["stale"] for obs in result["observations"])
    assert all(obs["stale_marker"] is False for obs in result["observations"])


@pytest.mark.asyncio
async def test_endpoint_serves_stored_values_when_refresh_fails(monkeypatch):
    old = datetime.now(timezone.utc) - timedelta(hours=8)
    async with AsyncSessionLocal() as db:
        for code, point in POINT_BY_CODE.items():
            db.add(
                SourceObservation(
                    point_code=code,
                    point_name=point["point_name"],
                    lat=point["latitude"],
                    lon=point["longitude"],
                    source="test",
                    source_url="https://example.test",
                    fetched_at=old,
                    payload={"summary": {"stale_marker": True}},
                )
            )
        await db.commit()

    def batch(points, now):
        raise DataUnavailableError("provider down")

    monkeypatch.setattr(
        "backend.ingestion.source_observations.fetch_points_batch", batch
    )

    async with AsyncSessionLocal() as db:
        result = await api_observations.latest_source_observations(db=db)

    assert result["count"] == len(POINT_BY_CODE)
    assert all(obs["stale"] for obs in result["observations"])
    assert all(obs["stale_marker"] is True for obs in result["observations"])
