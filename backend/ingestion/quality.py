"""Fail-closed input checks. Sample generators are for explicit offline tests only."""

import numpy as np


class DataUnavailableError(RuntimeError):
    """Required observed input, coverage or provenance is missing."""


def require_observed(data, source):
    if data is None or data.attrs.get("synthetic"):
        raise DataUnavailableError(f"{source}: observed input unavailable")
    if not np.isfinite(
        data.to_array().values if hasattr(data, "to_array") else data.values
    ).all():
        raise DataUnavailableError(f"{source}: missing or invalid cells")
    return data
