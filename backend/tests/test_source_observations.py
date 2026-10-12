"""Coverage for time windows and fail-closed provider ingestion."""

from datetime import datetime, timedelta, timezone
import pytest
from backend.ingestion.source_observations import summarize
from backend.ingestion.quality import DataUnavailableError


def response():
    now = datetime(2026, 10, 11, 12, tzinfo=timezone.utc)
    times = [now - timedelta(hours=72) + timedelta(hours=i) for i in range(121)]
    return now, {
        "latitude": 11.58,
        "longitude": 76.08,
        "hourly_units": {"rain": "mm"},
        "hourly": {
            "time": [t.isoformat().replace("+00:00", "") for t in times],
            "rain": [0] + [1] * 72 + [2] * 24 + [3] * 24,
            "soil_moisture_0_to_1cm": [0.2] * 121,
        },
    }


def test_exact_windows_distinguish_forecast_horizons():
    now, data = response()
    result = summarize(data, now)
    assert result["modeled_large_scale_rain_previous_72h_mm"] == 72
    assert result["modeled_large_scale_rain_previous_24h_mm"] == 24
    assert result["forecast_large_scale_rain_next_24h_mm"] == 48
    assert result["forecast_large_scale_rain_hours_24_to_48_mm"] == 72
    assert result["used_for_warnings"] is False
    assert result["is_sample"] is False


def test_null_input_is_never_zero():
    now, data = response()
    data["hourly"]["rain"][1] = None
    with pytest.raises(DataUnavailableError):
        summarize(data, now)


def test_missing_hours_are_rejected():
    now, data = response()
    for value in data["hourly"].values():
        del value[1]
    with pytest.raises(DataUnavailableError):
        summarize(data, now)


@pytest.mark.asyncio
async def test_status_history_and_no_sample_alerts_by_default():
    import uuid
    from httpx import AsyncClient, ASGITransport
    from backend.api.main import app
    from backend.api.database import AsyncSessionLocal
    from backend.models import SourceObservation

    now = datetime.now(timezone.utc)
    code = "T" + uuid.uuid4().hex[:6].upper()
    summary = {
        "modeled_large_scale_rain_previous_24h_mm": 1.5,
        "modeled_large_scale_rain_previous_72h_mm": 3.0,
        "forecast_large_scale_rain_next_24h_mm": 0.0,
        "modeled_soil_moisture_0_to_1cm_m3_m3": 0.2,
    }
    async with AsyncSessionLocal() as db:
        for age in (30, 90):
            db.add(
                SourceObservation(
                    point_code=code,
                    point_name="Test point",
                    lat=11.5,
                    lon=76.0,
                    source="Open-Meteo weather models",
                    source_url="https://api.open-meteo.com/v1/forecast",
                    fetched_at=now - timedelta(minutes=age),
                    payload={"summary": summary},
                )
            )
        await db.commit()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        st = (await c.get("/v1/status")).json()
        obs = st["source_observations"]
        assert obs["data_mode"] == "real_provider_values"
        assert obs["used_for_warnings"] is False
        assert obs["count"] >= 1
        h = await c.get(f"/v1/source-observations/{code}/history?hours=2")
        assert h.status_code == 200
        body = h.json()
        assert body["count"] == 2
        assert body["snapshots"][0]["fetched_at"] > body["snapshots"][1]["fetched_at"]
        assert body["used_for_warnings"] is False
        assert (await c.get("/v1/source-observations/NOPE/history")).status_code == 404
        alerts = (await c.get("/v1/alerts/active?min_fpi=0")).json()
        assert alerts["count"] == 0
        assert alerts["data_mode"] != "sample"


def test_registry_covers_19_states_preserves_all_existing_points():
    from backend.ingestion.point_registry import (
        POINTS,
        POINT_BY_CODE,
        coverage_metadata,
    )

    original = {
        "WAY": (11.58, 76.08),
        "IDK": (9.85, 76.97),
        "KOT": (9.59, 76.52),
        "NLG": (11.41, 76.69),
        "MND": (31.71, 76.93),
        "SKM": (27.33, 88.61),
    }
    assert len(POINTS) == len(POINT_BY_CODE) == 22
    assert coverage_metadata()["configured_state_ut_count"] == 19
    for code, (lat, lon) in original.items():
        assert (POINT_BY_CODE[code]["latitude"], POINT_BY_CODE[code]["longitude"]) == (
            lat,
            lon,
        )
    for point in POINT_BY_CODE.values():
        terrain = point["terrain"]
        assert 0 <= terrain["native_slope_degrees"] <= 90
        assert len(terrain["source_sha256"]) == 64
        assert terrain["used_for_warnings"] is False
        assert point["site_susceptibility_verified"] is False


def test_registry_rejects_duplicate_or_fake_warning_sites(tmp_path):
    import copy
    import json
    from backend.ingestion.point_registry import REGISTRY, load_registry

    path = tmp_path / "bad.json"
    bad = copy.deepcopy(REGISTRY)
    bad["points"].append(bad["points"][0])
    path.write_text(json.dumps(bad))
    with pytest.raises(DataUnavailableError):
        load_registry(path)
    bad = copy.deepcopy(REGISTRY)
    bad["points"][0]["terrain"]["used_for_warnings"] = True
    path.write_text(json.dumps(bad))
    with pytest.raises(DataUnavailableError):
        load_registry(path)


@pytest.mark.asyncio
async def test_busy_history_cannot_hide_a_less_recent_point():
    from httpx import AsyncClient, ASGITransport
    from backend.api.main import app
    from backend.api.database import AsyncSessionLocal
    from backend.models import SourceObservation

    now, data = response()
    summary = summarize(data, now)
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        for i in range(110):
            db.add(
                SourceObservation(
                    point_code="WAY",
                    point_name="Wayanad",
                    lat=11.58,
                    lon=76.08,
                    source="Open-Meteo weather models",
                    source_url="https://api.open-meteo.com/v1/forecast",
                    fetched_at=now - timedelta(minutes=i),
                    payload={"summary": summary},
                )
            )
        db.add(
            SourceObservation(
                point_code="SKM",
                point_name="Gangtok",
                lat=27.33,
                lon=88.61,
                source="Open-Meteo weather models",
                source_url="https://api.open-meteo.com/v1/forecast",
                fetched_at=now - timedelta(hours=2),
                payload={"summary": summary},
            )
        )
        await db.commit()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        body = (await client.get("/v1/source-observations")).json()
        assert body["count"] == 2
        assert body["configured_point_count"] == 22
        assert body["available_configured_point_count"] == 2
        assert len(body["missing_point_codes"]) == 20
        assert {r["point_code"] for r in body["observations"]} == {"WAY", "SKM"}
        assert all(
            r["terrain"]["used_for_warnings"] is False for r in body["observations"]
        )
        status = (await client.get("/v1/status")).json()["source_observations"]
        assert status["count"] == 2
        assert status["configured_state_ut_count"] == 19
