"""Audit NASA official current export and freeze event-level Stage3 membership."""

import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from training.audit_inventory import RAIN_TRIGGERS, ACCURACY


def audit(path, output):
    output.mkdir(parents=True, exist_ok=True)
    a = pd.read_csv(path)
    a["parsed_date"] = (
        pd.to_datetime(a.event_date, unit="ms", utc=True, errors="coerce")
        .dt.tz_localize(None)
        .dt.normalize()
    )
    a["provenance_status"] = "official_nasa_coolr_public_service"
    a["date_precision"] = "reported_calendar_date_local_timezone_unverified"
    accepted = a[
        a.country_name.eq("India")
        & a.landslide_trigger.isin(RAIN_TRIGGERS)
        & a.location_accuracy.isin(ACCURACY)
        & a.parsed_date.notna()
        & a.latitude.between(6, 38)
        & a.longitude.between(66, 98)
    ].copy()
    dup = accepted.duplicated(
        ["parsed_date", "latitude", "longitude"]
    ) | accepted.duplicated("event_id")
    accepted[dup].to_csv(output / "duplicate_exclusions.csv", index=False)
    accepted = accepted[~dup]
    accepted["spatial_group"] = (
        accepted.latitude.round().astype(str)
        + "_"
        + accepted.longitude.round().astype(str)
    )
    spatial = accepted.spatial_group.map(
        lambda x: int(hashlib.sha256(x.encode()).hexdigest()[:8], 16) % 5 == 0
    )
    year = accepted.parsed_date.dt.year
    accepted["split"] = np.select(
        [
            spatial & year.le(2016),
            spatial & year.ge(2017),
            ~spatial & year.le(2012),
            ~spatial & year.eq(2013),
            ~spatial & year.eq(2014),
            ~spatial & year.between(2015, 2016),
            ~spatial & year.ge(2017),
        ],
        [
            "legacy_spatial_diagnostic",
            "spatial_confirmation",
            "train",
            "calibration",
            "threshold",
            "legacy_temporal_diagnostic",
            "temporal_confirmation",
        ],
        "excluded",
    )
    accepted.to_csv(output / "candidate_events.csv", index=False)
    a.to_csv(output / "all_reports.csv", index=False)
    result = {
        "status": "official_source_not_validated",
        "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "candidates": len(accepted),
        "duplicates_removed": int(dup.sum()),
        "split_counts": accepted.split.value_counts().to_dict(),
        "year_counts": year.value_counts().sort_index().to_dict(),
        "time_nonmissing": int(accepted.event_time.notna().sum()),
        "local_event_timezone_verified": False,
        "warning_publication_enabled": False,
    }
    (output / "audit.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    audit(a.input, a.output)
