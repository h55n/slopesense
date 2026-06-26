"""Coverage for production integration fallbacks and orchestration helpers."""

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest


def test_model_trainer_download_filters_india(monkeypatch):
    from backend.model.train import ModelTrainer

    source = pd.DataFrame(
        {
            "latitude": [11.58, 42.0, 27.59],
            "longitude": [76.08, -120.0, 88.53],
            "event_date": ["2024-07-30", "2024-01-01", "2023-10-04"],
        }
    )
    monkeypatch.setattr(pd, "read_csv", lambda _: source)

    events = ModelTrainer().download_nasa_glc()

    assert list(events.columns) == ["lat", "lon", "event_date"]
    assert len(events) == 2
    assert events["lat"].between(6, 38).all()


def test_model_trainer_dataset_and_save(monkeypatch):
    from backend.model.train import ModelTrainer

    trainer = ModelTrainer()
    monkeypatch.setattr(
        trainer,
        "extract_features_for_event",
        lambda lat, lon, event_date: {
            "rainfall_3d_mm": 180.0,
            "soil_moisture_pct": 91.0,
            "slope_degrees": 31.0,
            "susceptibility_class": 4.0,
            "forecast_24h_mm": 80.0,
            "ndvi_delta": -0.1,
        },
    )
    events = pd.DataFrame(
        {
            "lat": [11.583, 27.59],
            "lon": [76.083, 88.53],
            "event_date": pd.to_datetime(["2024-07-30", "2023-10-04"], utc=True),
        }
    )

    X, y = trainer.build_training_dataset(events, negative_ratio=2)
    output_dir = Path(".test-artifacts/model")
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = trainer.save_model(object(), {"model": object(), "auc": 0.9}, output_dir=output_dir)

    assert X.shape[0] == 6
    assert int(y.sum()) == 2
    assert model_path.exists()
    assert (output_dir / "fpi_lgbm_india_v01_metrics.json").exists()


@pytest.mark.asyncio
async def test_dispatcher_dry_run_sends_development_contact(monkeypatch):
    from backend.alert.dispatcher import AlertDispatcher

    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("TEST_WHATSAPP_NUMBER", "+919876543210")

    alert = {
        "id": "alert-1",
        "should_notify": True,
        "district_code": "KL_WYD",
        "district_name": "Wayanad",
        "block_name": "Meppadi",
        "tier": "WARNING",
        "fpi_score": 0.73,
        "fpi_ci_lower": 0.61,
        "fpi_ci_upper": 0.84,
        "fpi_24h": 0.81,
        "rainfall_3d_mm": 183,
        "soil_moisture_percentile": 91,
        "dominant_signals": [{"signal": "rainfall_accumulation", "value": 0.82}],
        "issued_at": datetime.now(timezone.utc),
    }

    result = await AlertDispatcher().dispatch_alerts([alert])

    assert result["alerts_processed"] == 1
    assert result["messages_sent"] == 1


@pytest.mark.asyncio
async def test_whatsapp_bulk_skips_missing_numbers():
    from backend.alert.dispatcher import WhatsAppDispatcher

    dispatcher = WhatsAppDispatcher(api_token=None, phone_number_id=None)
    results = await dispatcher.send_bulk(
        [{"id": "missing"}, {"id": "ok", "whatsapp_number": "+919876543210", "language": "en"}],
        lambda contact, language: f"hello {language}",
        delay_between_ms=0,
    )

    assert len(results) == 1
    assert results[0]["status"] == "dry_run"
    assert results[0]["contact_id"] == "ok"


def test_email_digest_builds_table():
    from backend.alert.dispatcher import EmailDispatcher

    html = EmailDispatcher()._build_digest_html(
        [
            {
                "state_name": "Kerala",
                "district_name": "Wayanad",
                "block_name": "Meppadi",
                "tier": "WARNING",
                "fpi_score": 0.73,
                "rainfall_3d_mm": 183,
            }
        ],
        datetime.now(timezone.utc),
    )

    assert "Wayanad" in html
    assert "73%" in html


def test_copernicus_synthetic_fallbacks(monkeypatch):
    from backend.ingestion import copernicus

    temp_root = Path(".test-artifacts/copernicus")
    monkeypatch.setattr(copernicus.DEMProcessor, "DATA_DIR", temp_root / "dem")
    monkeypatch.setattr(copernicus.Sentinel2Ingestion, "DATA_DIR", temp_root / "sentinel2")
    bbox = {"min_lat": 11.3, "max_lat": 11.34, "min_lon": 75.7, "max_lon": 75.74}

    dem_processor = copernicus.DEMProcessor()
    dem = dem_processor._generate_synthetic_dem(bbox)
    slope, aspect = dem_processor._compute_slope_aspect(dem)

    sentinel = copernicus.Sentinel2Ingestion()
    ndvi = sentinel._generate_synthetic_ndvi(bbox)
    delta = sentinel._zero_delta(bbox)

    assert dem.shape == slope.shape == aspect.shape
    assert 0 <= dem_processor.classify_slope_risk(30) <= 1
    assert ndvi.name == "ndvi"
    assert float(delta.max()) == 0.0


def test_worker_configuration_and_lightweight_tasks(monkeypatch):
    import backend.worker as worker

    class Runner:
        def run_all(self, use_synthetic=True):
            return {"flagged_at_t24": 6}

    monkeypatch.setattr("backend.model.retrospective.RetrospectiveRunner", lambda: Runner())

    assert "model-run-00z" in worker.celery_app.conf.beat_schedule
    assert worker.send_whatsapp_alert.run("alert-1", "contact-1") is None
    assert worker.send_daily_digest.run() is None
    assert worker.run_retrospective.run() == {"flagged_at_t24": 6}
