"""Conservative event-time and grouping helpers for landslide research audits.

Reported catalog dates/times are not a precise local event instant. Candidate
storm groups are for split-leakage review, not evidence that reports share a storm.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import math
from typing import Iterable, Mapping, Sequence


def reported_event_time_semantics(event_date_epoch_ms, event_time_label=None):
    """Preserve NASA's source date representation without inventing local time.

    The source date field is encoded as epoch milliseconds; UTC rendering is
    metadata about its stored value, not proof of the event's local calendar day.
    The separate event_time field is an approximate catalog label with no verified
    local timezone. Therefore neither is sufficient to assert a 24-hour lead time.
    """
    if event_date_epoch_ms is None or not math.isfinite(float(event_date_epoch_ms)):
        stored_utc = None
        stored_utc_day = None
    else:
        stamp = datetime.fromtimestamp(
            float(event_date_epoch_ms) / 1000, tz=timezone.utc
        )
        stored_utc = stamp.isoformat().replace("+00:00", "Z")
        stored_utc_day = stamp.date().isoformat()

    label = "" if event_time_label is None else str(event_time_label).strip()
    known_label = bool(label) and label.lower() not in {
        "unknown",
        "none",
        "null",
        "nan",
    }
    if not known_label:
        label = "unknown" if label.lower() in {"unknown", "none", "null", "nan"} else ""
    return {
        "source_event_date_epoch_ms": event_date_epoch_ms,
        "source_event_date_rendered_utc": stored_utc,
        "source_event_date_utc_day": stored_utc_day,
        "event_time_source_label": label or None,
        "event_time_label_is_approximate": known_label,
        "event_local_timezone": "unknown_or_unverified",
        "event_local_instant_verified": False,
        "usable_for_24h_forecast_target": False,
        "24h_target_exclusion_reason": (
            "local event date/time and timezone are not verified"
        ),
    }


def catalog_label_semantics(label: int) -> dict:
    """Describe a case-control indicator without claiming verified safe negatives."""
    if label not in (0, 1):
        raise ValueError("label must be binary")
    return {
        "label_name": "reported_event_case",
        "label_interpretation": "reported-event case vs sampled background without nearby catalog report",
        "case_status": "catalog_reported_event"
        if label
        else "sampled_no_nearby_catalog_report",
        "negative_is_verified_non_event": False,
        "negative_is_verified_safe": False,
        "target_is_real_world_failure_probability": False,
    }


def exact_duplicate_groups(rows: Sequence[Mapping]):
    """Return stable exact-duplicate groups; never fuzzy-collapse reports.

    Group on explicit event_id, or, if absent, exact reported calendar day and
    exact coordinates. Nearby/near-date reports are kept for candidate storm
    clustering and human review rather than silently removed.
    """
    buckets = {}
    for index, row in enumerate(rows):
        event_id = row.get("event_id")
        if event_id is not None and str(event_id).strip() not in {"", "nan", "None"}:
            key = ("event_id", str(event_id).strip())
        else:
            day = str(
                row.get("reported_utc_calendar_date") or row.get("parsed_date") or ""
            )[:10]
            lat, lon = row.get("latitude"), row.get("longitude")
            if not day or lat is None or lon is None:
                key = ("row", index)
            else:
                key = ("date_exact_coordinate", day, float(lat), float(lon))
        buckets.setdefault(key, []).append(index)
    return [indices for indices in buckets.values() if len(indices) > 1]


def candidate_storm_groups(
    rows: Sequence[Mapping], *, radius_km: float, max_day_gap: int
):
    """Return connected components for sensitivity review before split freezing.

    Uses great-circle distance and reported-calendar-day gap. Parameters are
    mandatory so the caller must record the chosen sensitivity setting. A returned
    group is a possible shared storm/event, not a verified causal storm label.
    """
    if not math.isfinite(radius_km) or radius_km <= 0:
        raise ValueError("radius_km must be a positive finite value")
    if not isinstance(max_day_gap, int) or max_day_gap < 0:
        raise ValueError("max_day_gap must be a non-negative integer")

    count = len(rows)
    parent = list(range(count))

    def find(item):
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(left, right):
        a, b = find(left), find(right)
        if a != b:
            parent[max(a, b)] = min(a, b)

    def distance_km(a, b):
        lat1, lon1 = (
            math.radians(float(a["latitude"])),
            math.radians(float(a["longitude"])),
        )
        lat2, lon2 = (
            math.radians(float(b["latitude"])),
            math.radians(float(b["longitude"])),
        )
        dlat, dlon = lat2 - lat1, lon2 - lon1
        hav = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        return 6371.0088 * 2 * math.asin(min(1.0, math.sqrt(hav)))

    def parse_day(row):
        value = row.get("reported_utc_calendar_date") or row.get("parsed_date")
        if value is None:
            return None
        text = str(value)[:10]
        try:
            return datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            return None

    days = [parse_day(row) for row in rows]
    for left in range(count):
        if (
            days[left] is None
            or rows[left].get("latitude") is None
            or rows[left].get("longitude") is None
        ):
            continue
        for right in range(left + 1, count):
            if (
                days[right] is None
                or rows[right].get("latitude") is None
                or rows[right].get("longitude") is None
            ):
                continue
            if (
                abs((days[right] - days[left]).days) <= max_day_gap
                and distance_km(rows[left], rows[right]) <= radius_km
            ):
                union(left, right)

    components = {}
    for index in range(count):
        components.setdefault(find(index), []).append(index)
    result = [component for component in components.values() if len(component) > 1]
    result.sort(key=lambda group: min(str(rows[i].get("event_id", i)) for i in group))
    return result


def stable_group_id(rows: Sequence[Mapping], indices: Iterable[int]) -> str:
    """Build an order-independent ID for a candidate event group."""
    ids = sorted(str(rows[index].get("event_id", index)) for index in indices)
    digest = hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()[:16]
    return f"candidate-{digest}"
