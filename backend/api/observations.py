"""Separately labeled provider values, not FPI or landslide warnings."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from backend.api.database import get_db
from backend.models import SourceObservation
from backend.ingestion.point_registry import POINT_BY_CODE, coverage_metadata

router = APIRouter(prefix="/v1/source-observations", tags=["Source observations"])


async def _latest_rows(db):
    # Rank per point BEFORE limiting. A busy point must not hide other locations.
    ranked = select(
        SourceObservation.id,
        func.row_number()
        .over(
            partition_by=SourceObservation.point_code,
            order_by=(SourceObservation.fetched_at.desc(), SourceObservation.id.desc()),
        )
        .label("position"),
    ).subquery()
    result = await db.execute(
        select(SourceObservation)
        .join(ranked, SourceObservation.id == ranked.c.id)
        .where(ranked.c.position == 1)
        .order_by(SourceObservation.point_code)
    )
    return result.scalars().all()


@router.get("")
async def latest_source_observations(db=Depends(get_db)):
    try:
        rows = await _latest_rows(db)
    except Exception as exc:
        raise HTTPException(503, "Source observation store unavailable") from exc
    latest = {}
    now = datetime.now(timezone.utc)
    for row in rows:
        if row.point_code in latest:
            continue
        fetched = row.fetched_at
        if fetched.tzinfo is None:
            fetched = fetched.replace(tzinfo=timezone.utc)
        latest[row.point_code] = {
            "point_code": row.point_code,
            "point_name": row.point_name,
            "latitude": row.lat,
            "longitude": row.lon,
            "source": row.source,
            "source_url": row.source_url,
            "fetched_at": fetched.isoformat(),
            "stale": (now - fetched).total_seconds() > 3 * 3600,
            **row.payload["summary"],
            "state": POINT_BY_CODE.get(row.point_code, {}).get("state"),
            "terrain": POINT_BY_CODE.get(row.point_code, {}).get("terrain"),
        }
    return {
        "data_mode": "real_provider_values" if latest else "unavailable",
        "warning_publication_enabled": False,
        "note": "Open-Meteo weather model values, not NASA/satellite or gauge measurements. Representative points only, not complete district or unstable-slope coverage. Not used for landslide warnings. A retrieved value is not independently verified ground truth.",
        **coverage_metadata(),
        "available_configured_point_count": len(set(latest) & set(POINT_BY_CODE)),
        "missing_point_codes": sorted(set(POINT_BY_CODE) - set(latest)),
        "count": len(latest),
        "observations": list(latest.values()),
    }


STALE_AFTER_SECONDS = 3 * 3600


def _aware(ts):
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


async def source_observation_summary(db) -> dict:
    """Compact freshness summary of stored provider snapshots for status pages."""
    try:
        rows = await _latest_rows(db)
    except Exception:
        return {"data_mode": "unavailable", "count": 0}
    points = {}
    for row in rows:
        points.setdefault(row.point_code, row)
    if not points:
        return {"data_mode": "unavailable", "count": 0}
    now = datetime.now(timezone.utc)
    newest = max(_aware(r.fetched_at) for r in points.values())
    oldest = min(_aware(r.fetched_at) for r in points.values())
    return {
        "data_mode": "real_provider_values",
        "provider": "Open-Meteo weather models",
        **coverage_metadata(),
        "available_configured_point_count": len(set(points) & set(POINT_BY_CODE)),
        "missing_point_codes": sorted(set(POINT_BY_CODE) - set(points)),
        "count": len(points),
        "newest_fetched_at": newest.isoformat(),
        "oldest_fetched_at": oldest.isoformat(),
        "newest_age_minutes": int((now - newest).total_seconds() // 60),
        "oldest_age_minutes": int((now - oldest).total_seconds() // 60),
        "stale": (now - oldest).total_seconds() > STALE_AFTER_SECONDS,
        "used_for_warnings": False,
    }


@router.get("/{point_code}/history")
async def source_observation_history(
    point_code: str,
    hours: int = Query(48, ge=1, le=168),
    db=Depends(get_db),
):
    """Timestamped stored snapshots for one point, newest first. No interpolation."""
    from datetime import timedelta

    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    try:
        rows = (
            (
                await db.execute(
                    select(SourceObservation)
                    .where(
                        SourceObservation.point_code == point_code.upper(),
                        SourceObservation.fetched_at >= since,
                    )
                    .order_by(SourceObservation.fetched_at.desc())
                    .limit(200)
                )
            )
            .scalars()
            .all()
        )
    except Exception as exc:
        raise HTTPException(503, "Source observation store unavailable") from exc
    if not rows:
        raise HTTPException(404, "No stored snapshots for this point in the window")
    keys = (
        "modeled_large_scale_rain_previous_24h_mm",
        "modeled_large_scale_rain_previous_72h_mm",
        "forecast_large_scale_rain_next_24h_mm",
        "modeled_soil_moisture_0_to_1cm_m3_m3",
    )
    return {
        "point_code": rows[0].point_code,
        "point_name": rows[0].point_name,
        "source": rows[0].source,
        "window_hours": hours,
        "count": len(rows),
        "snapshots": [
            {
                "fetched_at": _aware(r.fetched_at).isoformat(),
                **{k: r.payload["summary"].get(k) for k in keys},
            }
            for r in rows
        ],
        "note": "Stored provider snapshots as fetched; not interpolated, not measurements, not used for warnings.",
        "used_for_warnings": False,
    }
