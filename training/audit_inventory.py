"""Audit an explicitly sourced inventory without guessing date/time or training labels.

Usage: python -m training.audit_inventory INPUT.csv OUTPUT_DIR
Candidate third-party mirrors remain unverified. No production/model files modified.
"""

import hashlib
import json
from pathlib import Path
import sys
import pandas as pd

RAIN_TRIGGERS = {"rain", "downpour", "continuous_rain", "monsoon", "tropical_cyclone"}
ACCURACY = {"exact", "1km", "5km"}


def audit(path, output):
    raw = Path(path).read_bytes()
    data = pd.read_csv(path)
    required = {
        "event_id",
        "event_date",
        "country_name",
        "latitude",
        "longitude",
        "landslide_trigger",
        "location_accuracy",
        "source_link",
    }
    if not required.issubset(data.columns):
        raise ValueError("Required source columns missing")
    data["parsed_date"] = pd.to_datetime(
        data.event_date, format="%m/%d/%Y %I:%M:%S %p", errors="coerce"
    )
    india = data[data.country_name.eq("India")].copy()
    accepted = india[
        india.landslide_trigger.isin(RAIN_TRIGGERS)
        & india.location_accuracy.isin(ACCURACY)
        & india.parsed_date.notna()
        & india.latitude.between(6, 38)
        & india.longitude.between(66, 98)
    ].copy()
    duplicates = accepted.duplicated(["parsed_date", "latitude", "longitude"])
    accepted = accepted[~duplicates]
    accepted["spatial_group"] = (
        accepted.latitude.round().astype(str)
        + "_"
        + accepted.longitude.round().astype(str)
    )
    accepted["provenance_status"] = "candidate_source_requires_verification"
    accepted["date_precision"] = "day_only_not_exact_time"
    destination = Path(output)
    destination.mkdir(parents=True, exist_ok=True)
    accepted.to_csv(destination / "candidate_events.csv", index=False)
    result = {
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "total_rows": len(data),
        "india_rows": len(india),
        "candidate_events": len(accepted),
        "duplicate_date_location_rows_removed": int(duplicates.sum()),
        "date_min": str(accepted.parsed_date.min()),
        "date_max": str(accepted.parsed_date.max()),
        "by_year": accepted.parsed_date.dt.year.value_counts().sort_index().to_dict(),
        "provenance_status": "unverified_until_authoritative_source_confirmed",
        "warning": "Day-only catalog entries cannot prove exact 24-hour warning lead time. Absence of report is not absence of landslide.",
    }
    (destination / "inventory_audit.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    audit(sys.argv[1], sys.argv[2])
