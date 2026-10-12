"""Persist real provider weather snapshots; never produce or deliver landslide alerts."""

import asyncio
from datetime import datetime, timezone, timedelta
import logging
import random
import time
from sqlalchemy import delete
from backend.api.database import AsyncSessionLocal, engine
from backend.models import SourceObservation
from backend.ingestion.source_observations import POINTS, fetch_point

logger = logging.getLogger(__name__)

MAX_CONSECUTIVE_FAILURES = 3
TIME_BUDGET_SECONDS = 8 * 60


async def run():
    now = datetime.now(timezone.utc)
    rows = []
    failed = []
    consecutive = 0
    started = time.monotonic()
    # Fetch before opening a transaction. A point that fails is skipped and reported;
    # earlier snapshots for it stay in the store and show as stale by age.
    for index, (code, name, lat, lon) in enumerate(POINTS):
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
    if len(rows) < max(1, len(POINTS) // 2):
        raise SystemExit(
            f"Only {len(rows)} of {len(POINTS)} points fetched; nothing persisted"
        )
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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
