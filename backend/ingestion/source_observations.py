"""Actual provider weather values. These are modeled weather, not satellite/gauge observations.

No synthetic fallback, percentile conversion, FPI scoring or alert dispatch occurs here.
"""

from datetime import datetime, timedelta, timezone
import math
import requests
import random
import time

from backend.ingestion.quality import DataUnavailableError
from backend.ingestion.point_registry import POINTS  # noqa: F401

API_URL = "https://api.open-meteo.com/v1/forecast"


def summarize(payload, now):
    """Exact hourly windows in UTC, never scaling a forecast into historical rainfall."""
    hourly = payload["hourly"]
    times = [
        datetime.fromisoformat(t).replace(tzinfo=timezone.utc) for t in hourly["time"]
    ]
    cutoff = now.replace(minute=0, second=0, microsecond=0)
    rain = hourly["rain"]
    soil = hourly["soil_moisture_0_to_1cm"]
    if not (len(times) == len(rain) == len(soil)):
        raise DataUnavailableError("Provider time/value lengths differ")
    if payload.get("hourly_units", {}).get("rain") != "mm":
        raise DataUnavailableError("Unexpected provider rainfall units")

    def window(start, end):
        values = [v for t, v in zip(times, rain) if start < t <= end]
        if len(values) != int((end - start).total_seconds() / 3600):
            raise DataUnavailableError("Incomplete rainfall time coverage")
        if any(v is None or not math.isfinite(v) or v < 0 for v in values):
            raise DataUnavailableError("Missing/invalid rainfall values")
        return round(sum(values), 3)

    current_soil = [v for t, v in zip(times, soil) if t == cutoff]
    if (
        len(current_soil) != 1
        or current_soil[0] is None
        or not 0 <= current_soil[0] <= 1
    ):
        raise DataUnavailableError("Missing/invalid modeled soil moisture")
    return {
        "window_end_utc": cutoff.isoformat(),
        "modeled_large_scale_rain_previous_72h_mm": window(
            cutoff - timedelta(hours=72), cutoff
        ),
        "modeled_large_scale_rain_previous_24h_mm": window(
            cutoff - timedelta(hours=24), cutoff
        ),
        "forecast_large_scale_rain_next_24h_mm": window(
            cutoff, cutoff + timedelta(hours=24)
        ),
        "forecast_large_scale_rain_hours_24_to_48_mm": window(
            cutoff + timedelta(hours=24), cutoff + timedelta(hours=48)
        ),
        "modeled_soil_moisture_0_to_1cm_m3_m3": current_soil[0],
        "provider_grid_latitude": payload["latitude"],
        "provider_grid_longitude": payload["longitude"],
        "provider_elevation_m": payload.get("elevation"),
        "data_kind": "weather_model_output_not_measured_satellite_data",
        "rain_semantics": "Large-scale rain only, excludes convective showers; values sum preceding hours",
        "attribution": "Open-Meteo, CC BY 4.0",
        "is_sample": False,
        "used_for_warnings": False,
    }


def fetch_point(
    lat, lon, now=None, max_attempts=3, sleep=time.sleep, jitter=random.uniform
):
    """Bounded retries for rate limits/transient failures. Never invent a value.

    Retry-After is honored up to120seconds; larger limits stop this batch. Missing
    or invalid data and permanent4xx responses are not retried.
    """
    now = now or datetime.now(timezone.utc)
    for attempt in range(max_attempts):
        try:
            response = requests.get(
                API_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "hourly": "rain,soil_moisture_0_to_1cm",
                    "past_days": 3,
                    "forecast_days": 3,
                    "timezone": "UTC",
                },
                timeout=30,
            )
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == max_attempts - 1:
                    response.raise_for_status()
                retry_after = response.headers.get("Retry-After", "")
                try:
                    delay = float(retry_after) if retry_after else 15 * 2**attempt
                except ValueError:
                    delay = 15 * 2**attempt
                if delay > 120:
                    raise DataUnavailableError(
                        "Provider requested long retry delay; batch aborted"
                    )
                sleep(max(0, delay) + jitter(1, 3))
                continue
            response.raise_for_status()
            payload = response.json()
            summary = summarize(payload, now)
            return response.url, {"summary": summary, "provider_response": payload}
        except (requests.Timeout, requests.ConnectionError):
            if attempt == max_attempts - 1:
                raise
            sleep(15 * 2**attempt + jitter(1, 3))
    raise DataUnavailableError("Provider retry budget exhausted")
