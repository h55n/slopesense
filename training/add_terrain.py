"""Public Copernicus DSM windows, native-pixel slope, no synthetic terrain fill."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
import requests
import rasterio
from rasterio.windows import Window

STAC = "https://earth-search.aws.element84.com/v1/search"
TERRAIN_FEATURES = ["elevation_mean_m", "slope_mean_deg", "slope_p90_deg", "relief_m"]


def sample(lat, lon, cache):
    key = hashlib.sha256(f"{lat:.6f},{lon:.6f}".encode()).hexdigest()
    dest = cache / (key + ".json")
    if dest.exists():
        return json.loads(dest.read_text())
    tilekey = f"{math.floor(lat)}_{math.floor(lon)}"
    tilepath = cache / ("tile_" + tilekey + ".json")
    if tilepath.exists():
        item = json.loads(tilepath.read_text())
    else:
        r = requests.get(
            STAC,
            params={
                "collections": "cop-dem-glo-30",
                "bbox": f"{lon-0.00001},{lat-0.00001},{lon+0.00001},{lat+0.00001}",
                "limit": 4,
            },
            timeout=30,
        )
        r.raise_for_status()
        items = r.json().get("features", [])
        if not items:
            raise ValueError("No public DEM coverage")
        item = items[0]
        tilepath.write_text(json.dumps(item))
    href = item["assets"]["data"]["href"]
    # Asset is an authoritative STAC-returned S3 locator; GDAL handles unsigned reads.
    if not href.startswith("s3://copernicus-dem-30m/"):
        raise ValueError("Unexpected source locator")
    with rasterio.Env(
        AWS_NO_SIGN_REQUEST="YES", GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"
    ):
        with rasterio.open(href) as src:
            row, col = src.index(lon, lat)
            pixels = 35  # ~1km patch; native resolution retained before gradient
            half = pixels // 2
            if (
                row < half
                or col < half
                or row + half >= src.height
                or col + half >= src.width
            ):
                raise ValueError(
                    "Patch crosses tile border; mosaic required, no clipped substitution"
                )
            arr = src.read(
                1, window=Window(col - half, row - half, pixels, pixels), masked=True
            )
            if np.ma.getmaskarray(arr).any() or not np.isfinite(arr).all():
                raise ValueError("DEM patch missing pixels")
            y_m = abs(src.transform.e) * 111132
            x_m = abs(src.transform.a) * 111320 * math.cos(math.radians(lat))
            dy, dx = np.gradient(np.asarray(arr, dtype=float), y_m, x_m)
            slopes = np.degrees(np.arctan(np.hypot(dx, dy)))[1:-1, 1:-1]
            result = {
                "elevation_mean_m": float(arr.mean()),
                "slope_mean_deg": float(slopes.mean()),
                "slope_p90_deg": float(np.percentile(slopes, 90)),
                "relief_m": float(arr.max() - arr.min()),
                "terrain_asset": href,
                "terrain_item": item["id"],
                "terrain_collection": "cop-dem-glo-30",
                "terrain_release": "AWS public2021 release",
                "terrain_native_resolution_m": 30,
                "terrain_post_event": True,
                "terrain_kind": "DSM includes canopy/buildings",
                "terrain_retrieved_at": datetime.now(timezone.utc).isoformat(),
                "terrain_patch_sha256": hashlib.sha256(
                    np.asarray(arr).tobytes()
                ).hexdigest(),
                "terrain_window_pixels": pixels,
                "terrain_crs": str(src.crs),
            }
    np.save(cache / (key + ".npy"), np.asarray(arr))
    dest.write_text(json.dumps(result))
    return result


def run(dataset, output, limit):
    output.mkdir(exist_ok=True, parents=True)
    cache = output / "terrain_cache"
    cache.mkdir(exist_ok=True)
    data = pd.read_csv(dataset)
    points = data[["event_id", "latitude", "longitude"]].drop_duplicates().head(limit)
    terrain = {}
    errors = []

    def get_point(p):
        return p.event_id, sample(p.latitude, p.longitude, cache)

    pool = ThreadPoolExecutor(max_workers=4)
    jobs = {
        pool.submit(get_point, p): p.event_id for p in points.itertuples(index=False)
    }
    for job in as_completed(jobs):
        event_id = jobs[job]
        try:
            event_id, values = job.result()
            terrain[event_id] = values
        except Exception as exc:
            errors.append(
                {
                    "event_id": int(event_id),
                    "type": type(exc).__name__,
                    "detail": str(exc)[:200],
                }
            )
        print(
            "terrain", event_id, "ok" if event_id in terrain else "failed", flush=True
        )
        joined = data[data.event_id.isin(terrain)].copy()
        for field in list(next(iter(terrain.values())).keys()) if terrain else []:
            joined[field] = joined.event_id.map(lambda x: terrain[x][field])
        joined.to_csv(output / "dataset_terrain.csv", index=False)
        (output / "terrain_errors.json").write_text(json.dumps(errors, indent=2))
    pool.shutdown()
    (output / "manifest.json").write_text(
        json.dumps(
            {
                "points_requested": len(points),
                "points_success": len(terrain),
                "source": "https://registry.opendata.aws/copernicus-dem/",
                "features": TERRAIN_FEATURES,
                "publication_enabled": False,
                "post_event_terrain": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--limit", type=int, default=5)
    a = p.parse_args()
    run(a.dataset, a.output, a.limit)
