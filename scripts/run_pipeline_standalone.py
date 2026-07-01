"""
Standalone Script to Run FPI Pipeline directly to Supabase.
Intended to be run by GitHub Actions cron.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

# Add the project root to sys.path so that 'backend' module is resolvable
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

from backend.api.database import AsyncSessionLocal
from backend.processing.preprocessor import DataPreprocessor
from backend.model.fpi_engine import FPIEngine
from backend.alert.alert_engine import AlertEngine
from backend.alert.dispatcher import AlertDispatcher
from backend.models import Alert, FPIHistory, PipelineRunLog
from sqlalchemy.future import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run():
    import time
    start_time = time.time()
    run_time = datetime.now(timezone.utc)
    logger.info(f"Pipeline: starting scheduled run at {run_time.isoformat()}")

    async with AsyncSessionLocal() as db:
        run_log = PipelineRunLog(
            run_timestamp=run_time,
            status="RUNNING"
        )
        db.add(run_log)
        await db.commit()
        await db.refresh(run_log)

        try:
            # 1. Preprocess
            preprocessor = DataPreprocessor()
            feature_grid = preprocessor.build_feature_grid(run_time=run_time)

            # 2. FPI
            engine = FPIEngine()
            cell_fpis = engine.compute_grid(feature_grid)

            block_map = {}
            block_fpis = engine.aggregate_to_blocks(cell_fpis, block_map)

            # Load previous alerts from DB
            result = await db.execute(select(Alert).where(Alert.is_active.is_(True)))
            prev_rows = result.scalars().all()
            prev_alerts = {}
            for r in prev_rows:
                prev_alerts[r.block_code] = {
                    "id": str(r.id),
                    "block_code": r.block_code,
                    "tier": r.tier.value if hasattr(r.tier, "value") else r.tier,
                    "consecutive_cycles": r.consecutive_cycles,
                    "is_active": r.is_active
                }

            # 3. Alert Engine
            alert_engine = AlertEngine(db_session=db)
            new_alerts, expired = await alert_engine.evaluate_blocks(block_fpis, prev_alerts)

            # Deactivate expired alerts
            for exp in expired:
                bc = exp["block_code"]
                db_alert = next((a for a in prev_rows if a.block_code == bc), None)
                if db_alert:
                    db_alert.is_active = False
                    db_alert.cleared_at = exp["cleared_at"]

            # Insert/Update new alerts
            for na in new_alerts:
                # If there's an existing active alert for this block, update it
                existing = next((a for a in prev_rows if a.block_code == na["block_code"] and a.is_active), None)
                if existing:
                    existing.fpi_score = na["fpi_score"]
                    existing.fpi_ci_lower = na["fpi_ci_lower"]
                    existing.fpi_ci_upper = na["fpi_ci_upper"]
                    existing.fpi_24h = na["fpi_24h"]
                    existing.tier = na["tier"]
                    existing.consecutive_cycles = na["consecutive_cycles"]
                    existing.rainfall_3d_mm = na["rainfall_3d_mm"]
                    existing.soil_moisture_percentile = na["soil_moisture_percentile"]
                else:
                    import uuid
                    db.add(Alert(
                        id=uuid.UUID(na["id"]),
                        alert_code=na["alert_code"],
                        state_code=na["state_code"],
                        state_name=na["state_name"],
                        district_code=na["district_code"],
                        district_name=na["district_name"],
                        block_code=na["block_code"],
                        block_name=na["block_name"],
                        lat=na["lat"],
                        lon=na["lon"],
                        fpi_score=na["fpi_score"],
                        fpi_ci_lower=na["fpi_ci_lower"],
                        fpi_ci_upper=na["fpi_ci_upper"],
                        fpi_24h=na["fpi_24h"],
                        tier=na["tier"],
                        is_active=na["is_active"],
                        is_suppressed=na["is_suppressed"],
                        consecutive_cycles=na["consecutive_cycles"],
                        issued_at=na["issued_at"],
                        rainfall_3d_mm=na["rainfall_3d_mm"],
                        soil_moisture_percentile=na["soil_moisture_percentile"]
                    ))

            await db.commit()

            # 4. Dispatch
            dispatcher = AlertDispatcher(db_session=db)
            dispatch_result = await dispatcher.dispatch_alerts(new_alerts)

            logger.info(f"Pipeline complete! active_alerts={len(new_alerts)}")

            run_log.status = "SUCCESS"
            run_log.records_processed = len(cell_fpis)
            run_log.alerts_generated = len(new_alerts)

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            run_log.status = "FAILED"
            run_log.error_message = str(e)
            raise
        finally:
            run_log.duration_seconds = time.time() - start_time
            db.add(run_log)
            await db.commit()

if __name__ == "__main__":
    asyncio.run(run())
