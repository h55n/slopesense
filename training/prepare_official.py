"""Audit NASA official current export and freeze event-level Stage3 membership."""

import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from training.audit_inventory import RAIN_TRIGGERS, ACCURACY
from training.event_quality import (
    candidate_storm_groups,
    reported_event_time_semantics,
    stable_group_id,
)


def audit(path, output):
    output.mkdir(parents=True, exist_ok=True)
    a = pd.read_csv(path)
    # Keep an explicitly UTC-aware rendering of NASA's stored epoch date. This
    # is not the event's locally verified calendar day or an exact local instant.
    a["source_event_date_epoch_ms"] = a.event_date
    a["parsed_date"] = pd.to_datetime(
        a.event_date, unit="ms", utc=True, errors="coerce"
    ).dt.normalize()
    time_meta = a.apply(
        lambda row: reported_event_time_semantics(row.event_date, row.event_time),
        axis=1,
    ).apply(pd.Series)
    for column in time_meta:
        a[column] = time_meta[column]
    a["provenance_status"] = "official_nasa_coolr_public_service"
    a["date_precision"] = (
        "catalog_epoch_date_utc_rendered; local_timezone_and_instant_unverified"
    )
    accepted = a[
        a.country_name.eq("India")
        & a.landslide_trigger.isin(RAIN_TRIGGERS)
        & a.location_accuracy.isin(ACCURACY)
        & a.parsed_date.notna()
        & a.latitude.between(6, 38)
        & a.longitude.between(66, 98)
    ].copy()
    # Keep the first occurrence for exact duplicate keys and record why every
    # removed row was classified as a duplicate.
    dup_event_id = accepted.duplicated("event_id", keep="first")
    dup_exact_location_day = accepted.duplicated(
        ["parsed_date", "latitude", "longitude"], keep="first"
    )
    dup = dup_event_id | dup_exact_location_day
    excluded = accepted[dup].copy()
    excluded["duplicate_reason"] = np.select(
        [dup_event_id.loc[dup].to_numpy(), dup_exact_location_day.loc[dup].to_numpy()],
        ["repeated_event_id", "exact_utc_date_coordinate"],
        default="exact_duplicate_key",
    )
    excluded.to_csv(output / "duplicate_exclusions.csv", index=False)
    accepted = accepted[~dup].copy()
    # Candidate clusters are only a split-leakage audit. They do not assert that
    # catalog reports describe a single verified storm or event.
    candidate_rows = accepted[
        ["event_id", "parsed_date", "latitude", "longitude"]
    ].to_dict("records")
    for row in candidate_rows:
        row["reported_utc_calendar_date"] = row.pop("parsed_date")
    candidate_groups = candidate_storm_groups(
        candidate_rows, radius_km=10, max_day_gap=3
    )
    accepted["candidate_storm_group"] = [
        f"event-{event_id}" for event_id in accepted.event_id
    ]
    accepted["candidate_storm_group_review_only"] = False
    accepted["candidate_storm_cluster_radius_km"] = 10
    accepted["candidate_storm_cluster_max_day_gap"] = 3
    for indices in candidate_groups:
        group_id = stable_group_id(candidate_rows, indices)
        accepted.iloc[indices, accepted.columns.get_loc("candidate_storm_group")] = (
            group_id
        )
        accepted.iloc[
            indices, accepted.columns.get_loc("candidate_storm_group_review_only")
        ] = True
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
        "event_local_instant_verified": False,
        "usable_for_24h_forecast_target": False,
        "candidate_storm_clusters_review_only": int(len(candidate_groups)),
        "candidate_storm_cluster_radius_km": 10,
        "candidate_storm_cluster_max_day_gap": 3,
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
