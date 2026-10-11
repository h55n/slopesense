"""Create non-spatial API persistence tables without seeding invented observations.

Run with DATABASE_URL in the environment. No credentials are printed.
"""

import asyncio

from backend.api.database import engine
from sqlalchemy import text
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
        if conn.dialect.name == "postgresql":
            # Older release created naive columns but inserted aware UTC defaults.
            for table, column in [
                ("api_keys", "created_at"),
                ("alert_contacts", "registered_at"),
                ("alert_contacts", "updated_at"),
                ("alerts", "cleared_at"),
                ("alerts", "expires_at"),
                ("alerts", "issued_at"),
                ("alerts", "updated_at"),
                ("alerts", "validated_at"),
                ("fpi_history", "run_timestamp"),
                ("pipeline_run_logs", "run_timestamp"),
            ]:
                await conn.execute(text(f"""
                    DO $$ BEGIN
                        IF EXISTS (SELECT 1 FROM information_schema.columns
                            WHERE table_schema = 'public' AND table_name = '{table}'
                            AND column_name = '{column}' AND data_type = 'timestamp without time zone') THEN
                            ALTER TABLE {table} ALTER COLUMN {column} TYPE TIMESTAMPTZ
                            USING {column} AT TIME ZONE 'UTC';
                        END IF;
                    END $$;
                """))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
