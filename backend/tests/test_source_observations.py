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
