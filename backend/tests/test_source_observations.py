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
