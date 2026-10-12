"""Frozen historical NASA input preparation; no production warning action."""

import requests
import pandas as pd
import xarray as xr
import pathlib
import json
import re
import concurrent.futures
import os
from urllib.parse import urljoin

out = pathlib.Path("/downloads/lhasa-larger")
x = pd.read_csv(out / "frozen_rows.csv")
static = pathlib.Path("/downloads/pretrained-lhasa/static")
datasets = {f.stem: xr.open_dataset(f) for f in static.glob("*.nc4")}
rows = []
for _, r in x.iterrows():
    v = r.to_dict()
    lat = float(datasets["Slope"].lat.sel(lat=r.latitude, method="nearest"))
    lon = float(datasets["Slope"].lon.sel(lon=r.longitude, method="nearest"))
    v["static_lat"] = lat
    v["static_lon"] = lon
    for n in ["Lithology", "Slope", "pga"]:
        v[n] = float(datasets[n][n].sel(lat=lat, lon=lon, method="nearest"))
    v["mask"] = int(datasets["mask"].land_mask.sel(lat=lat, lon=lon, method="nearest"))
    v["p99"] = float(datasets["p99"].p99.sel(lat=lat, lon=lon, method="nearest"))
    d = pd.Timestamp(r.target_date)
    for age, run in [(0, "E"), (1, "L"), (2, "L")]:
        v["rainkey" + str(age)] = (
            run + "_" + (d - pd.Timedelta(days=age)).strftime("%Y%m%d")
        )
    v["smap_actual_time"] = (d - pd.Timedelta(days=2, hours=1)).floor(
        "3h"
    ) + pd.Timedelta(hours=1, minutes=30)
    v["smap_actual_time"] = v["smap_actual_time"].isoformat()
    rows.append(v)
json.dump(rows, open(out / "rows_static.json", "w"), indent=2)
months = sorted(
    set(
        (v["rainkey" + str(a)][0], v["rainkey" + str(a)][2:8])
        for v in rows
        for a in range(3)
    )
)
listing = out / "listings"
listing.mkdir(exist_ok=True)


def fetch(m):
    run, month = m
    p = listing / (run + "_" + month + ".json")
    if p.exists():
        return
    base = (
        "https://jsimpsonhttps.pps.eosdis.nasa.gov/imerg/gis/"
        + ("early/" if run == "E" else "")
        + month[:4]
        + "/"
        + month[4:]
        + "/"
    )
    try:
        rr = requests.get(
            base, auth=(os.environ["PPS_LOGIN"], os.environ["PPS_LOGIN"]), timeout=25
        )
        rr.raise_for_status()
        links = {}
        for f in re.findall(r'href="([^"]+\.1day\.zip)"', rr.text):
            d = re.search(r"3IMERG\.(\d{8})-S233000", f)
            if d:
                links[run + "_" + d[1]] = urljoin(base, f)
        json.dump({"base": base, "links": links}, open(p, "w"))
    except Exception as e:
        print("listing error", m, str(e), flush=True)


with concurrent.futures.ThreadPoolExecutor(3) as pool:
    list(pool.map(fetch, months))
print(
    "monthly listings",
    len(months),
    "actual",
    len(list(listing.glob("*.json"))),
    flush=True,
)
