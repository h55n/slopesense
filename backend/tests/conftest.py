"""
SlopeSense — pytest configuration and shared fixtures.
"""

import os
import sys
import pytest
import pytest_asyncio
import sqlalchemy
from sqlalchemy import event
from sqlalchemy import event

import numpy as np
from datetime import datetime, timezone
from pathlib import Path

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Force in-memory SQLite for all tests — no external DB required
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ.setdefault("WHATSAPP_API_TOKEN", "")
os.environ.setdefault("NASA_EARTHDATA_USERNAME", "")
os.environ.setdefault("NASA_EARTHDATA_PASSWORD", "")
os.environ["API_KEYS"] = "test-api-key"

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    from backend.api.database import engine
    from backend.models import Base
    
    @event.listens_for(engine.sync_engine, "before_cursor_execute", retval=True)
    def skip_spatialite_functions(conn, cursor, statement, parameters, context, executemany):
        if any(func in statement for func in [
            "CheckSpatialIndex", "RecoverGeometryColumn", "DisableSpatialIndex",
            "CreateSpatialIndex", "AddGeometryColumn", "DiscardGeometryColumn"
        ]):
            return "SELECT 1", ()
        return statement, parameters
    
    # Enable SQLite in-memory or file-based tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
@pytest.fixture
def wayanad_bbox():
    return {"min_lat": 11.3, "max_lat": 11.9, "min_lon": 75.7, "max_lon": 76.4}


@pytest.fixture
def uttarakhand_bbox():
    return {"min_lat": 29.5, "max_lat": 31.5, "min_lon": 78.0, "max_lon": 81.0}


@pytest.fixture
def sample_fpi_features():
    """Realistic FPI feature set for Wayanad conditions."""
    return {
        "rainfall_3d_mm": 183.0,
        "rainfall_24h_mm": 95.0,
        "forecast_24h_mm": 80.0,
        "forecast_48h_mm": 60.0,
        "soil_moisture_pct": 91.0,
        "soil_moisture_abs": 0.40,
        "slope_degrees": 34.0,
        "aspect_degrees": 270.0,
        "elevation_m": 850.0,
        "ndvi_delta": -0.02,
        "susceptibility_class": 5.0,
    }


@pytest.fixture
def sample_alert():
    return {
        "id": "test-alert-001",
        "alert_code": "KL_WYD_MEP_TEST",
        "tier": "WARNING",
        "state_code": "KL",
        "state_name": "Kerala",
        "district_code": "KL_WYD",
        "district_name": "Wayanad",
        "block_code": "KL_WYD_MEP",
        "block_name": "Meppadi",
        "fpi_score": 0.73,
        "fpi_ci_lower": 0.61,
        "fpi_ci_upper": 0.84,
        "fpi_24h": 0.81,
        "is_active": True,
        "is_suppressed": False,
        "consecutive_cycles": 2,
        "dominant_signals": [{"signal": "rainfall_accumulation", "value": 0.82}],
        "rainfall_3d_mm": 183.0,
        "soil_moisture_percentile": 91.0,
        "cell_count_total": 48,
        "cell_count_breached": 22,
        "breach_fraction": 0.46,
        "should_notify": True,
        "issued_at": datetime.now(timezone.utc),
    }


@pytest.fixture
def mock_feature_grid(wayanad_bbox):
    """Minimal FeatureGrid for unit tests without satellite data."""
    from backend.processing.preprocessor import FeatureGrid
    import numpy as np

    lats = np.arange(wayanad_bbox["min_lat"], wayanad_bbox["max_lat"] + 0.1, 0.1)
    lons = np.arange(wayanad_bbox["min_lon"], wayanad_bbox["max_lon"] + 0.1, 0.1)
    shape = (len(lats), len(lons))

    return FeatureGrid(
        lats=lats,
        lons=lons,
        run_timestamp=datetime(2024, 7, 29, 6, 0, 0),
        rainfall_3d_mm=np.full(shape, 183.0),
        rainfall_24h_mm=np.full(shape, 95.0),
        forecast_24h_mm=np.full(shape, 80.0),
        forecast_48h_mm=np.full(shape, 60.0),
        soil_moisture_pct=np.full(shape, 91.0),
        soil_moisture_abs=np.full(shape, 0.40),
        slope_degrees=np.full(shape, 34.0),
        aspect_degrees=np.full(shape, 270.0),
        elevation_m=np.full(shape, 850.0),
        ndvi_delta=np.full(shape, -0.02),
        susceptibility_class=np.full(shape, 5),
        rainfall_synthetic=True,
        smap_synthetic=True,
        dem_synthetic=True,
    )
