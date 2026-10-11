"""Official ORNL retrospective NDVI; completed pre-event composite, QA fail closed."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta, datetime, timezone
import hashlib
import json
from pathlib import Path
import requests
import numpy as np
import pandas as pd

ROOT = "https://modis.ornl.gov/rst/api/v1/MOD13Q1"


def get(url, params, cache):
    request = requests.Request("GET", url, params=params).prepare()
    path = cache / (hashlib.sha256(request.url.encode()).hexdigest() + ".json")
    if path.exists():
        return json.loads(path.read_text())
    r = requests.get(url, params=params, timeout=45)
    r.raise_for_status()
    doc = {
        "url": r.url,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "raw": r.json(),
    }
    path.write_text(json.dumps(doc))
    return doc


def point(frame, cache):
    lat = float(frame.iloc[0].latitude)
    lon = float(frame.iloc[0].longitude)
    dates = get(ROOT + "/dates", {"latitude": lat, "longitude": lon}, cache)["raw"][
        "dates"
    ]
    targets = {}
    for d in frame.target_date:
        cutoff = str(date.fromisoformat(d) - timedelta(days=35))
        eligible = [x for x in dates if x["calendar_date"] <= cutoff]
        if not eligible:
            raise ValueError("No pre-event composite")
        targets[d] = eligible[-1]
    # Sparse requests, one per needed composite; cache removes duplicate windows.
    features = {}
    for target, composite in targets.items():
        doc = get(
            ROOT + "/subset",
            {
                "latitude": lat,
                "longitude": lon,
                "startDate": composite["modis_date"],
                "endDate": composite["modis_date"],
                "kmAboveBelow": 1,
                "kmLeftRight": 1,
            },
            cache,
        )
        raw = doc["raw"]
        bands = {b["band"]: b for b in raw["subset"]}
        ndvi = bands["250m_16_days_NDVI"]
        quality = bands["250m_16_days_pixel_reliability"]
        a = np.array(ndvi["data"], dtype=float)
        q = np.array(quality["data"])
        if a.shape != q.shape or len(a) != raw["nrows"] * raw["ncols"]:
            raise ValueError("Patch dimensions disagree")
        good = (q == 0) & (a >= -2000) & (a <= 10000)
        if good.mean() < 0.25:
            raise ValueError("Insufficient good-quality NDVI pixels")
        if ndvi["calendar_date"] != composite["calendar_date"]:
            raise ValueError("Returned composite date mismatch")
        features[target] = {
            "ndvi_mean": float(a[good].mean() * 0.0001),
            "ndvi_good_fraction": float(good.mean()),
            "ndvi_composite_start": ndvi["calendar_date"],
            "ndvi_processing_date": ndvi.get("proc_date"),
            "ndvi_pixel_size_m": raw["cellsize"],
            "ndvi_source_url": doc["url"],
            "ndvi_retrospective": True,
        }
    return int(frame.iloc[0].event_id), features


def run(dataset, output, limit):
    output.mkdir(exist_ok=True, parents=True)
    cache = output / "ndvi_cache"
    cache.mkdir(exist_ok=True)
    data = pd.read_csv(dataset)
    groups = list(data.groupby("event_id", sort=False))[:limit]
    results = {}
    errors = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = {pool.submit(point, g, cache): i for i, g in groups}
        for job in as_completed(jobs):
            ident = jobs[job]
            try:
                ident, features = job.result()
                results[ident] = features
            except Exception as exc:
                errors.append(
                    {
                        "event_id": int(ident),
                        "type": type(exc).__name__,
                        "detail": str(exc)[:200],
                    }
                )
            print("ndvi", ident, "ok" if ident in results else "failed", flush=True)
            joined = data[data.event_id.isin(results)].copy()
            for field in (
                list(next(iter(next(iter(results.values())).values())).keys())
                if results
                else []
            ):
                joined[field] = [
                    results[int(r.event_id)][r.target_date][field]
                    for r in joined.itertuples(index=False)
                ]
            joined.to_csv(output / "dataset_ndvi.csv", index=False)
            (output / "ndvi_errors.json").write_text(json.dumps(errors, indent=2))
    (output / "manifest.json").write_text(
        json.dumps(
            {
                "requested_groups": len(groups),
                "successful_groups": len(results),
                "publication_enabled": False,
                "source": "https://modis.ornl.gov/data/modis_webservice.html",
                "group_exclusion": "any missing row excludes whole group",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--limit", type=int, default=3)
    a = p.parse_args()
    run(a.dataset, a.output, a.limit)
