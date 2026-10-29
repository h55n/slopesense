"""Persist real provider weather snapshots; never produce or deliver landslide alerts."""

import asyncio
from datetime import datetime, timezone, timedelta
import logging
import random
import time
from sqlalchemy import delete, func, select
from backend.api.database import AsyncSessionLocal, engine
from backend.models import SourceObservation
from backend.ingestion.source_observations import POINTS, fetch_point

logger = logging.getLogger(__name__)

MAX_CONSECUTIVE_FAILURES = 3
TIME_BUDGET_SECONDS = 8 * 60


async def oldest_first(points):
    """Visit never-fetched and oldest points first, retaining registry tie order."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SourceObservation.point_code, func.max(SourceObservation.fetched_at))
            .where(SourceObservation.point_code.in_([point[0] for point in points]))
            .group_by(SourceObservation.point_code)
        )
        latest = dict(result.all())
    never = datetime.min.replace(tzinfo=timezone.utc)

    def fetched_at(point):
        value = latest.get(point[0])
        if value is None:
            return never
        # SQLite returns naive UTC datetimes; PostgreSQL returns aware values.
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value

    return sorted(points, key=fetched_at)


async def run():
    points = await oldest_first(POINTS)
    now = datetime.now(timezone.utc)
    rows = []
    failed = []
    consecutive = 0
    started = time.monotonic()
    # Fetch before opening a transaction. A point that fails is skipped and reported;
    # earlier snapshots for it stay in the store and show as stale by age.
    for index, (code, name, lat, lon) in enumerate(points):
        if consecutive >= MAX_CONSECUTIVE_FAILURES or (
            time.monotonic() - started > TIME_BUDGET_SECONDS
        ):
            failed.append(code)
            continue
        if index:
            # Shared runner IPs can hit provider limits. Hourly 22 point batch stays
            # below 10 requests/minute; jitter avoids repeated burst alignment.
            await asyncio.sleep(7 + random.uniform(0, 2))
        try:
            url, payload = await asyncio.to_thread(fetch_point, lat, lon, now)
        except Exception as exc:
            logger.warning("Point %s skipped: %s", code, type(exc).__name__)
            failed.append(code)
            consecutive += 1
            continue
        consecutive = 0
        rows.append(
            SourceObservation(
                point_code=code,
                point_name=name,
                lat=lat,
                lon=lon,
                source="Open-Meteo weather models",
                source_url=url,
                fetched_at=now,
                payload=payload,
            )
        )
    insufficient = len(rows) < max(1, len(POINTS) // 2)
    if not rows:
        await engine.dispose()
        raise SystemExit(f"Only 0 of {len(POINTS)} points fetched; nothing persisted")
    async with AsyncSessionLocal() as db:
        db.add_all(rows)
        # Bound free-tier storage, preserving the recent audit trail.
        await db.execute(
            delete(SourceObservation).where(
                SourceObservation.fetched_at < now - timedelta(days=30)
            )
        )
        await db.commit()
    logger.info(
        "Persisted %s provider snapshots. No warning scores computed.", len(rows)
    )
    if failed:
        logger.warning("Missing this run (previous values keep their age): %s", failed)
    await engine.dispose()
    if insufficient:
        raise SystemExit(
            f"Only {len(rows)} of {len(POINTS)} points fetched; "
            "successful snapshots persisted, refresh remains incomplete"
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
