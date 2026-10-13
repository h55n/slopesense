"""Cached real ERA5 feature joins for exploratory reported-event classification.

Never a production warning model. Background label means no catalog report,
not a confirmed non-event. Day-only event uncertainty precludes exact lead-time claims.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import pandas as pd
import requests

API = "https://archive-api.open-meteo.com/v1/archive"
FEATURES = ["rain_3d_mm", "rain_7d_mm", "rain_14d_mm", "soil_mean_3d", "soil_mean_14d"]


def feature_window(lat, lon, target, cache):
    # Exclude the preceding day as well as event day: conservative calendar-day gap.
    end = target - pd.Timedelta(days=2)
    start = end - pd.Timedelta(days=13)
    params = {
        "latitude": float(lat),
        "longitude": float(lon),
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": end.strftime("%Y-%m-%d"),
        "daily": "precipitation_sum",
        "hourly": "soil_moisture_0_to_7cm",
        "models": "era5",
        "timezone": "UTC",
    }
    key = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
    path = cache / (key + ".json")
    if path.exists():
        envelope = json.loads(path.read_text())
    else:
        response = requests.get(API, params=params, timeout=40)
        response.raise_for_status()
        envelope = {
            "source_url": response.url,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "params": params,
            "response": response.json(),
        }
        path.write_text(json.dumps(envelope))
        time.sleep(0.4)  # <=150 requests/minute, below free 600/minute limit
    data = envelope["response"]
    rain = np.array(data["daily"]["precipitation_sum"], dtype=float)
    soil = np.array(data["hourly"]["soil_moisture_0_to_7cm"], dtype=float)
    if (
        len(rain) != 14
        or len(soil) != 14 * 24
        or not np.isfinite(rain).all()
        or not np.isfinite(soil).all()
    ):
        raise ValueError("Incomplete weather coverage; no zero fill")
    if (rain < 0).any() or (soil < 0).any() or (soil > 1).any():
        raise ValueError("Invalid physical value")
    return {
        "rain_3d_mm": float(rain[-3:].sum()),
        "rain_7d_mm": float(rain[-7:].sum()),
        "rain_14d_mm": float(rain.sum()),
        "soil_mean_3d": float(soil[-72:].mean()),
        "soil_mean_14d": float(soil.mean()),
        "weather_cache_key": key,
        "feature_end_date": end.strftime("%Y-%m-%d"),
        "source_url": envelope["source_url"],
    }


def background_dates(event, all_reports, count=3):
    # Fixed seed and season-local temporal controls. All India reports, not filtered positives,
    # are used for exclusion, including unknown triggers/poor accuracy.
    seed = int(hashlib.sha256(str(event.event_id).encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    day = pd.Timestamp(event.parsed_date)
    near = all_reports[(all_reports.latitude - event.latitude).abs() < 0.25]
    near = near[(near.longitude - event.longitude).abs() < 0.30]
    candidates = [
        day + pd.Timedelta(days=int(offset))
        for offset in rng.permutation(np.arange(-90, 91))
    ]
    result = []
    for candidate in candidates:
        if candidate.year != day.year:
            continue
        if (abs(near.parsed_date - candidate) <= pd.Timedelta(days=30)).any():
            continue
        if any(abs(candidate - x) < pd.Timedelta(days=14) for x in result):
            continue
        result.append(candidate)
        if len(result) == count:
            break
    return result


def run(events_path, raw_path, output, limit):
    output.mkdir(parents=True, exist_ok=True)
    cache = output / "weather_cache"
    cache.mkdir(exist_ok=True)
    events = pd.read_csv(events_path, parse_dates=["parsed_date"])
    reports = pd.read_csv(raw_path)
    reports["parsed_date"] = pd.to_datetime(reports.parsed_date)
    reports = reports[reports.country_name.eq("India") & reports.parsed_date.notna()]
    prior = output / "dataset.csv"
    rows = pd.read_csv(prior).to_dict("records") if prior.exists() else []
    errors_path = output / "errors.json"
    errors = json.loads(errors_path.read_text()) if errors_path.exists() else []
    done = set(r["event_id"] for r in rows) | set(r["event_id"] for r in errors)
    # Resume only after complete per-event checkpoint; interrupted event has no written rows.

    for event in events.head(limit).itertuples():
        if event.event_id in done:
            continue
        targets = [(event.parsed_date, 1)] + [
            (d, 0) for d in background_dates(event, reports)
        ]

        def fetch_target(pair, event=event):
            target, label = pair
            identity = {
                "event_id": event.event_id,
                "target_date": str(target.date()),
                "label": label,
                "label_meaning": (
                    "reported_rainfall_landslide_case"
                    if label
                    else "sampled_no_nearby_catalog_report_not_verified_non_event_or_safe"
                ),
                "label_name": "reported_event_case",
                "label_interpretation": "reported-event case vs sampled background without nearby catalog report",
                "negative_is_verified_non_event": False,
                "negative_is_verified_safe": False,
                "target_is_real_world_failure_probability": False,
                "event_local_timezone": event.event_local_timezone,
                "event_local_instant_verified": False,
                "usable_for_24h_forecast_target": False,
                "candidate_storm_group": event.candidate_storm_group,
                "candidate_storm_group_review_only": event.candidate_storm_group_review_only,
                "latitude": event.latitude,
                "longitude": event.longitude,
                "spatial_group": event.spatial_group,
                "provenance_status": "official_nasa_coolr_public_service",
                "weather_model": "era5_reanalysis",
                "split": event.split,
                "weather_resolution": "0.25_degree_approximately_28km",
            }
            try:
                return {
                    **identity,
                    **feature_window(event.latitude, event.longitude, target, cache),
                }, None
            except Exception as exc:
                return None, {
                    **identity,
                    "error_type": type(exc).__name__,
                    "detail": str(exc)[:200],
                }

        # Three workers, each delayed >=0.4s, theoretical ceiling450/minute
        # plus network latency, below the free600/minute limit. Bounded per-event.
        with ThreadPoolExecutor(max_workers=3) as pool:
            for row, error in pool.map(fetch_target, targets):
                if row is not None:
                    rows.append(row)
                else:
                    errors.append(error)
        pd.DataFrame(rows).to_csv(output / "dataset.csv", index=False)
        (output / "errors.json").write_text(json.dumps(errors, indent=2))
        print(
            f"event={event.event_id} rows={len(rows)} failures={len(errors)}",
            flush=True,
        )
        if (
            errors
            and errors[-1]["error_type"] == "HTTPError"
            and any(x in errors[-1]["detail"] for x in ["429", "403"])
        ):
            raise RuntimeError(
                "Provider throttling/challenge: stopped rather than retrying"
            )
    (output / "manifest.json").write_text(
        json.dumps(
            {
                "events_requested": min(limit, len(events)),
                "rows": len(rows),
                "failures": len(errors),
                "features": FEATURES,
                "inventory_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
                "purpose": "exploratory_hindcast_not_operational_forecast",
                "publication_enabled": False,
                "label_name": "reported_event_case",
                "label_interpretation": "reported-event case vs sampled background without nearby catalog report",
                "negative_is_verified_non_event": False,
                "negative_is_verified_safe": False,
                "exact_local_event_times_verified": False,
                "usable_for_24h_forecast_target": False,
                "candidate_storm_clustering": {
                    "radius_km": 10,
                    "max_day_gap": 3,
                    "review_only": True,
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--events", type=Path, required=True)
    p.add_argument("--raw", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--limit", type=int, default=10)
    args = p.parse_args()
    run(args.events, args.raw, args.output, args.limit)
