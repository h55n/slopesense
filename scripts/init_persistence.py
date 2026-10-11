"""Create non-spatial API persistence tables without seeding invented observations.

Run with DATABASE_URL in the environment. No credentials are printed.
"""

import asyncio

from backend.api.database import engine
from backend.models import (
    ApiKey,
    AlertContact,
    Alert,
    PipelineRunLog,
    FPIHistory,
    SourceObservation,
)


async def main():
    tables = [
        ApiKey.__table__,
        AlertContact.__table__,
        Alert.__table__,
        PipelineRunLog.__table__,
        FPIHistory.__table__,
        SourceObservation.__table__,
    ]
    async with engine.begin() as conn:
        for table in tables:
            await conn.run_sync(lambda sync, t=table: t.create(sync, checkfirst=True))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
