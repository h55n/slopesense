"""Separately labeled provider values, not FPI or landslide warnings."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from backend.api.database import get_db
from backend.models import SourceObservation

router = APIRouter(prefix="/v1/source-observations", tags=["Source observations"])


@router.get("")
async def latest_source_observations(db=Depends(get_db)):
    try:
        rows = (
            (
                await db.execute(
                    select(SourceObservation)
                    .order_by(SourceObservation.fetched_at.desc())
                    .limit(100)
                )
            )
            .scalars()
            .all()
        )
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
        }
    return {
        "data_mode": "real_provider_values" if latest else "unavailable",
        "warning_publication_enabled": False,
        "note": "Open-Meteo weather model values, not NASA/satellite or gauge measurements. Six representative points only, not complete district coverage. Not used for landslide warnings. A retrieved value is not independently verified ground truth.",
        "count": len(latest),
        "observations": list(latest.values()),
    }
