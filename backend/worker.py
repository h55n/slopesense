"""
SlopeSense — Celery Worker + APScheduler

Runs the FPI pipeline every 6 hours (monsoon: every 6h; off-season: every 24h).
Handles:
  - Scheduled model runs
  - Alert dispatch tasks
  - Daily email digest
  - Retrospective validation (run once on startup if not cached)
"""

import asyncio
import logging
import os
from datetime import datetime, timezone

from celery import Celery
from celery.schedules import crontab

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "slopesense",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,

    # Beat schedule — 6-hourly model runs aligned to GFS runs (00Z, 06Z, 12Z, 18Z)
    beat_schedule={
        "model-run-00z": {
            "task": "worker.run_model_pipeline",
            "schedule": crontab(hour="0,6,12,18", minute="30"),  # 30min after GFS
            "options": {"priority": 5},
        },
        "daily-email-digest": {
            "task": "worker.send_daily_digest",
            "schedule": crontab(hour="6", minute="0"),  # 6am UTC = 11:30am IST
            "options": {"priority": 3},
        },
        "retrospective-refresh": {
            "task": "worker.run_retrospective",
            "schedule": crontab(day_of_week="monday", hour="2", minute="0"),
            "options": {"priority": 1},
        },
    },
)


@celery_app.task(name="worker.run_model_pipeline", bind=True, max_retries=2)
def run_model_pipeline(self):
    """
    Full pipeline task: ingest → preprocess → FPI → alert → dispatch.
    Runs every 6 hours.
    """
    logger.info(f"Worker: starting model pipeline run at {datetime.now(timezone.utc).isoformat()}")
    try:
        import httpx

        internal_url = os.environ.get("API_BASE_URL", "http://localhost:8000")
        token = os.environ.get("INTERNAL_TRIGGER_TOKEN", "dev-token")

        resp = httpx.post(
            f"{internal_url}/internal/trigger-run",
            params={"token": token},
            timeout=600,
        )

        if resp.status_code == 200:
            result = resp.json()
            logger.info(f"Worker: pipeline complete — {result}")
            return result
        else:
            raise Exception(f"Pipeline trigger failed: HTTP {resp.status_code} — {resp.text}")

    except Exception as exc:
        logger.error(f"Worker: pipeline failed: {exc}")
        raise self.retry(exc=exc, countdown=300)  # retry in 5 minutes


@celery_app.task(name="worker.send_whatsapp_alert")
def send_whatsapp_alert(alert_id: str, contact_id: str, language: str = "en"):
    """
    Send a single WhatsApp alert message.
    Queued individually per contact for retry control.
    """
    logger.info(f"Worker: sending WhatsApp alert {alert_id} → {contact_id}")
    try:
        # In production: load alert and contact from DB, dispatch
        pass
    except Exception as e:
        logger.error(f"Worker: WhatsApp send failed: {e}")
        raise


@celery_app.task(name="worker.send_daily_digest")
def send_daily_digest():
    """Send daily HTML email digest to SDMA contacts."""
    logger.info("Worker: sending daily digest")
    try:
        # In production: load active alerts, build digest, send emails
        pass
    except Exception as e:
        logger.error(f"Worker: digest failed: {e}")


@celery_app.task(name="worker.run_retrospective")
def run_retrospective():
    """Run retrospective validation on all historical events."""
    logger.info("Worker: running retrospective validation")
    try:
        import sys
        sys.path.insert(0, "/app")
        from backend.model.retrospective import RetrospectiveRunner
        runner = RetrospectiveRunner()
        summary = runner.run_all(use_synthetic=True)
        logger.info(f"Worker: retrospective complete — {summary['flagged_at_t24']}/6 flagged")
        return summary
    except Exception as e:
        logger.error(f"Worker: retrospective failed: {e}")
        raise


# ── Standalone scheduler (APScheduler, used without Celery in dev) ────────────

def start_apscheduler():
    """
    Start APScheduler for development use (no Redis/Celery required).
    """
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = AsyncIOScheduler(timezone="UTC")

    async def _trigger_pipeline():
        import httpx
        token = os.environ.get("INTERNAL_TRIGGER_TOKEN", "dev-token")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "http://localhost:8000/internal/trigger-run",
                    params={"token": token},
                    timeout=600,
                )
                logger.info(f"Scheduler: pipeline triggered — {resp.status_code}")
        except Exception as e:
            logger.error(f"Scheduler: trigger failed: {e}")

    scheduler.add_job(
        _trigger_pipeline,
        CronTrigger(hour="0,6,12,18", minute="30"),
        id="model_run",
        name="FPI Model Run",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("APScheduler started — model runs at 00:30, 06:30, 12:30, 18:30 UTC")
    return scheduler


if __name__ == "__main__":
    # Run worker directly: python -m backend.worker
    celery_app.start()
