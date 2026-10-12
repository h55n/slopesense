import requests
import json
import pathlib
import concurrent.futures
import hashlib
import zipfile
import io
import re
import sys
import numpy as np
import rasterio
from rasterio.windows import Window

out = pathlib.Path("/downloads/lhasa-larger")
cache = out / "rain_crops"
cache.mkdir(exist_ok=True)
rows = json.load(open(out / "rows_static.json"))
links = {}
for p in (out / "listings").glob("*.json"):
    links.update(json.load(open(p))["links"])
jobs = {}
for r in rows:
    for a in range(3):
        jobs.setdefault(r["rainkey" + str(a)], []).append(r)
need = [kv for kv in jobs.items() if not (cache / (kv[0] + ".json")).exists()][
    : int(sys.argv[1])
]


def work(kv):
    key, rr = kv
    url = links.get(key)
    if not url:
        return
    try:
        r = requests.get(
            url,
            auth=(
                __import__("os").environ["PPS_LOGIN"],
                __import__("os").environ["PPS_LOGIN"],
            ),
            timeout=45,
        )
        r.raise_for_status()
        sha = hashlib.sha256(r.content).hexdigest()
        z = zipfile.ZipFile(io.BytesIO(r.content))
        files = [n for n in z.namelist() if n.endswith(".liquid.tif")]
        assert len(files) == 1
        with rasterio.MemoryFile(z.read(files[0])) as mem, mem.open() as src:
            values = []
            for row in rr:
                y, x = src.index(row["static_lon"], row["static_lat"])
                win = Window(x - 1, y - 1, 3, 3)
                data = src.read(1, window=win)
                assert data.shape == (3, 3)
                p = cache / (key + "_" + str(row["event_id"]) + ".tif")
                profile = src.profile.copy()
                profile.update(height=3, width=3, transform=src.window_transform(win))
                with rasterio.open(p, "w", **profile) as d:
                    d.write(data, 1)
                val = float(data[1, 1])
                assert np.isfinite(val) and 0 <= val < 30000
                values.append(
                    {
                        "event_id": row["event_id"],
                        "mm": val / 10,
                        "crop": str(p),
                        "lat": row["static_lat"],
                        "lon": row["static_lon"],
                    }
                )
        json.dump(
            {
                "key": key,
                "url": url,
                "source_zip_sha256": sha,
                "version": re.search(r"V(07\w)", url)[1],
                "values": values,
            },
            open(cache / (key + ".json"), "w"),
        )
    except Exception as e:
        json.dump(
            {"key": key, "error": str(e)}, open(cache / (key + ".error.json"), "w")
        )


with concurrent.futures.ThreadPoolExecutor(3) as pool:
    list(pool.map(work, need))
print(
    "needed",
    len(jobs),
    "done",
    len(list(cache.glob("*.json"))),
    "this_batch",
    len(need),
    flush=True,
)
