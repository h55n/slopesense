"""Versioned representative points. Descriptive terrain is not a warning model."""

import math

from backend.ingestion.quality import DataUnavailableError
from backend.ingestion.point_registry_data import REGISTRY_DATA


def load_registry(registry=None):
    registry = REGISTRY_DATA if registry is None else registry
    codes = set()
    for point in registry["points"]:
        code = point["point_code"]
        lat, lon = point["latitude"], point["longitude"]
        slope = point["terrain"]["native_slope_degrees"]
        if (
            code in codes
            or not all(math.isfinite(v) for v in (lat, lon, slope))
            or not -90 <= lat <= 90
            or not -180 <= lon <= 180
            or not 0 <= slope <= 90
            or point["site_susceptibility_verified"] is not False
            or point["terrain"]["used_for_warnings"] is not False
        ):
            raise DataUnavailableError("Invalid representative point registry")
        codes.add(code)
    return registry


REGISTRY = load_registry()
POINT_BY_CODE = {p["point_code"]: p for p in REGISTRY["points"]}
POINTS = [
    (p["point_code"], p["point_name"], p["latitude"], p["longitude"])
    for p in REGISTRY["points"]
]


def coverage_metadata():
    return {
        "registry_version": REGISTRY["version"],
        "configured_point_count": len(POINTS),
        "configured_state_ut_count": len({p["state"] for p in REGISTRY["points"]}),
        "coverage_scope": REGISTRY["scope"],
        "regional_scope_source": REGISTRY["regional_scope_source"],
    }
