"""Persist real provider weather snapshots; never produce or deliver landslide alerts."""

import asyncio
from datetime import datetime, timezone, timedelta
import logging
import random
from sqlalchemy import delete
from backend.api.database import AsyncSessionLocal, engine
from backend.models import SourceObservation
from backend.ingestion.source_observations import POINTS, fetch_point

logger = logging.getLogger(__name__)


async def run():
    now = datetime.now(timezone.utc)
    rows = []
    # Fetch every point before opening a transaction. Any failed point aborts the run.
    for index, (code, name, lat, lon) in enumerate(POINTS):
        if index:
            # Shared runner IPs can hit provider limits. Hourly22pointbatch stays
            # below10requests/minute; jitter avoids repeatedburstalignment.
            await asyncio.sleep(7 + random.uniform(0, 2))
        url, payload = await asyncio.to_thread(fetch_point, lat, lon, now)
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
    await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
