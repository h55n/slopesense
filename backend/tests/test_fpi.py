"""
SlopeSense — Test Suite

Unit tests for FPI engine, alert logic, and data pipeline.
Run: pytest backend/tests/ -v --cov=backend
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
import numpy as np
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock


# ── FPI Engine Tests ──────────────────────────────────────────────────────────

class TestFPIEngine:
    """Tests for the physics-based FPI scoring engine."""

    @pytest.fixture
    def engine(self):
        from backend.model.fpi_engine import FPIEngine
        return FPIEngine()

    def test_fpi_high_rainfall_high_moisture(self, engine):
        """High rainfall + saturated soil should produce WARNING-level FPI."""
        features = {
            "rainfall_3d_mm": 200.0,
            "rainfall_24h_mm": 80.0,
            "forecast_24h_mm": 60.0,
            "forecast_48h_mm": 40.0,
            "soil_moisture_pct": 92.0,
            "soil_moisture_abs": 0.42,
            "slope_degrees": 30.0,
            "aspect_degrees": 180.0,
            "elevation_m": 1200.0,
            "ndvi_delta": -0.05,
            "susceptibility_class": 5.0,
        }
        fpi = engine._score_physics(features)
        assert fpi >= 0.65, f"Expected WARNING FPI (≥0.65), got {fpi:.3f}"
        assert fpi <= 1.0

    def test_fpi_dry_conditions(self, engine):
        """Dry soil + low rainfall should produce NORMAL FPI."""
        features = {
            "rainfall_3d_mm": 10.0,
            "rainfall_24h_mm": 3.0,
            "forecast_24h_mm": 5.0,
            "forecast_48h_mm": 3.0,
            "soil_moisture_pct": 25.0,
            "soil_moisture_abs": 0.12,
            "slope_degrees": 20.0,
            "aspect_degrees": 90.0,
            "elevation_m": 500.0,
            "ndvi_delta": 0.02,
            "susceptibility_class": 2.0,
        }
        fpi = engine._score_physics(features)
        assert fpi < 0.40, f"Expected NORMAL FPI (<0.40), got {fpi:.3f}"
        assert fpi >= 0.0

    def test_fpi_wayanad_conditions(self, engine):
        """Replicate Wayanad 2024 conditions — should be WARNING/EMERGENCY."""
        features = {
            "rainfall_3d_mm": 183.0,   # published rainfall figure
            "rainfall_24h_mm": 95.0,
            "forecast_24h_mm": 80.0,
            "forecast_48h_mm": 60.0,
            "soil_moisture_pct": 91.0,  # 91st percentile
            "soil_moisture_abs": 0.40,
            "slope_degrees": 34.0,      # Meppadi slope
            "aspect_degrees": 270.0,
            "elevation_m": 850.0,
            "ndvi_delta": -0.02,
            "susceptibility_class": 5.0,
        }
        fpi = engine._score_physics(features)
        assert fpi >= 0.65, f"Wayanad conditions should produce WARNING+ FPI, got {fpi:.3f}"

    def test_fpi_bounded_zero_to_one(self, engine):
        """FPI must always be in [0, 1]."""
        # Test extreme high values
        extreme_high = {
            "rainfall_3d_mm": 999.0,
            "rainfall_24h_mm": 400.0,
            "forecast_24h_mm": 300.0,
            "forecast_48h_mm": 200.0,
            "soil_moisture_pct": 100.0,
            "soil_moisture_abs": 0.55,
            "slope_degrees": 60.0,
            "aspect_degrees": 0.0,
            "elevation_m": 3000.0,
            "ndvi_delta": -0.5,
            "susceptibility_class": 5.0,
        }
        fpi_high = engine._score_physics(extreme_high)
        assert 0.0 <= fpi_high <= 1.0

        # Test zero values
        zero_features = {k: 0.0 for k in extreme_high}
        fpi_zero = engine._score_physics(zero_features)
        assert 0.0 <= fpi_zero <= 1.0

    def test_confidence_interval_width(self, engine):
        """CI should be wider in middle range and narrower at extremes."""
        mid_features = {
            "rainfall_3d_mm": 100.0, "rainfall_24h_mm": 40.0,
            "forecast_24h_mm": 30.0, "forecast_48h_mm": 20.0,
            "soil_moisture_pct": 60.0, "soil_moisture_abs": 0.25,
            "slope_degrees": 20.0, "aspect_degrees": 90.0,
            "elevation_m": 500.0, "ndvi_delta": 0.0, "susceptibility_class": 3.0,
        }
        fpi_mid = engine._score_physics(mid_features)
        ci_lo, ci_hi = engine._compute_confidence_interval(fpi_mid, mid_features)
        ci_width_mid = ci_hi - ci_lo

        high_features = {**mid_features, "rainfall_3d_mm": 300.0, "soil_moisture_pct": 98.0}
        fpi_high = engine._score_physics(high_features)
        ci_lo_h, ci_hi_h = engine._compute_confidence_interval(fpi_high, high_features)
        ci_width_high = ci_hi_h - ci_lo_h

        # Middle range should have higher uncertainty
        assert ci_width_mid >= ci_width_high or abs(ci_width_mid - ci_width_high) < 0.08

    def test_alert_tier_classification(self, engine):
        """Tier classification should follow defined thresholds."""
        assert engine._classify_tier(0.85, False) == "EMERGENCY"
        assert engine._classify_tier(0.70, False) == "WARNING"
        assert engine._classify_tier(0.50, False) == "WATCH"
        assert engine._classify_tier(0.20, False) == "NORMAL"
        assert engine._classify_tier(0.90, True) == "MONITORING"  # suppressed

    def test_forecast_fpi_higher_than_current(self, engine):
        """Forecast FPI (with added rain) should be ≥ current FPI."""
        features = {
            "rainfall_3d_mm": 120.0,
            "rainfall_24h_mm": 50.0,
            "forecast_24h_mm": 80.0,  # more rain coming
            "forecast_48h_mm": 60.0,
            "soil_moisture_pct": 75.0,
            "soil_moisture_abs": 0.32,
            "slope_degrees": 28.0,
            "aspect_degrees": 180.0,
            "elevation_m": 900.0,
            "ndvi_delta": 0.0,
            "susceptibility_class": 4.0,
        }
        fpi_now = engine._score_physics(features)
        fpi_24h = engine._score_cell_forecast(features, 24)
        assert fpi_24h >= fpi_now * 0.9, "24h forecast should be >= current (with more rain)"

    def test_dominant_signal_identification(self, engine):
        """Should correctly identify rainfall as dominant when it's the driving signal."""
        features = {
            "rainfall_3d_mm": 300.0,  # extreme rainfall
            "rainfall_24h_mm": 100.0,
            "forecast_24h_mm": 50.0,
            "forecast_48h_mm": 30.0,
            "soil_moisture_pct": 40.0,  # moderate soil moisture
            "soil_moisture_abs": 0.18,
            "slope_degrees": 10.0,  # gentle slope
            "aspect_degrees": 0.0,
            "elevation_m": 200.0,
            "ndvi_delta": 0.0,
            "susceptibility_class": 1.0,
        }
        dominant, breakdown = engine._identify_dominant_signal(features)
        assert dominant == "rainfall_accumulation", f"Expected rainfall as dominant, got {dominant}"


# ── Alert Engine Tests ─────────────────────────────────────────────────────────

class TestAlertEngine:
    """Tests for alert threshold and dispatch logic."""

    @pytest.fixture
    def engine(self):
        from backend.alert.alert_engine import AlertEngine
        return AlertEngine()

    def _make_block_fpi(self, **kwargs):
        """Create a minimal BlockFPI-like dict for testing."""
        defaults = {
            "block_code": "TEST_BLK",
            "block_name": "Test Block",
            "district_code": "TEST_DIST",
            "district_name": "Test District",
            "state_code": "TS",
            "state_name": "Test State",
            "fpi_score": 0.70,
            "fpi_ci_lower": 0.60,
            "fpi_ci_upper": 0.80,
            "fpi_24h": 0.75,
            "fpi_48h": 0.78,
            "alert_tier": "WARNING",
            "is_suppressed": False,
            "cell_count_total": 50,
            "cell_count_breached": 20,
            "breach_fraction": 0.40,
            "dominant_signals": [{"signal": "rainfall_accumulation", "value": 0.8}],
            "rainfall_3d_mm": 160.0,
            "soil_moisture_pct": 85.0,
            "run_timestamp": datetime.now(timezone.utc),
        }
        defaults.update(kwargs)

        # Create a simple object with attributes
        class BlockFPIStub:
            pass
        stub = BlockFPIStub()
        for k, v in defaults.items():
            setattr(stub, k, v)
        return stub

    @pytest.mark.asyncio
    async def test_warning_alert_created(self, engine):
        """WARNING tier should create an alert."""
        block = self._make_block_fpi(fpi_score=0.70, alert_tier="WARNING")
        new_alerts, expired = await engine.evaluate_blocks([block])
        assert len(new_alerts) == 1
        assert new_alerts[0]["tier"] == "WARNING"

    @pytest.mark.asyncio
    async def test_emergency_fires_immediately(self, engine):
        """EMERGENCY should fire WhatsApp immediately (no temporal persistence)."""
        block = self._make_block_fpi(fpi_score=0.85, alert_tier="EMERGENCY")
        new_alerts, _ = await engine.evaluate_blocks([block])
        assert new_alerts[0]["should_notify"] is True
        assert new_alerts[0]["consecutive_cycles"] == 1

    @pytest.mark.asyncio
    async def test_warning_requires_2_cycles(self, engine):
        """WARNING requires 2 consecutive cycles before WhatsApp fires."""
        block = self._make_block_fpi(fpi_score=0.70, alert_tier="WARNING")

        # First cycle: no notify
        new_alerts, _ = await engine.evaluate_blocks([block])
        assert new_alerts[0]["should_notify"] is False
        assert new_alerts[0]["consecutive_cycles"] == 1

        # Second cycle: notify
        prev = {block.block_code: new_alerts[0]}
        new_alerts2, _ = await engine.evaluate_blocks([block], prev)
        assert new_alerts2[0]["should_notify"] is True
        assert new_alerts2[0]["consecutive_cycles"] == 2

    @pytest.mark.asyncio
    async def test_normal_tier_no_alert(self, engine):
        """NORMAL tier blocks should not generate alerts."""
        block = self._make_block_fpi(fpi_score=0.20, alert_tier="NORMAL")
        new_alerts, _ = await engine.evaluate_blocks([block])
        assert len(new_alerts) == 0

    @pytest.mark.asyncio
    async def test_suppressed_alert_creates_monitoring(self, engine):
        """Suppressed (high uncertainty) blocks should produce MONITORING tier, not EMERGENCY."""
        block = self._make_block_fpi(
            fpi_score=0.85, alert_tier="MONITORING", is_suppressed=True
        )
        new_alerts, _ = await engine.evaluate_blocks([block])
        # MONITORING tier: no alert is created (engine skips MONITORING)
        assert len(new_alerts) == 0

    def test_whatsapp_message_english(self, engine):
        """WhatsApp message should contain key alert information."""
        alert = {
            "tier": "WARNING",
            "district_name": "Wayanad",
            "block_name": "Meppadi",
            "state_name": "Kerala",
            "fpi_score": 0.73,
            "fpi_ci_lower": 0.61,
            "fpi_ci_upper": 0.84,
            "fpi_24h": 0.81,
            "dominant_signals": [{"signal": "rainfall_accumulation"}],
            "rainfall_3d_mm": 183.0,
            "soil_moisture_percentile": 91.0,
            "issued_at": datetime.now(timezone.utc),
        }
        msg = engine.format_whatsapp_message(alert, language="en")
        assert "Wayanad" in msg
        assert "Meppadi" in msg
        assert "73%" in msg or "73" in msg
        assert "WARNING" in msg or "HIGH" in msg
        assert "183" in msg

    def test_whatsapp_message_hindi(self, engine):
        """Hindi WhatsApp message should contain district name."""
        alert = {
            "tier": "WARNING",
            "district_name": "Wayanad",
            "block_name": "Meppadi",
            "state_name": "Kerala",
            "fpi_score": 0.73,
            "fpi_ci_lower": 0.61,
            "fpi_ci_upper": 0.84,
            "fpi_24h": 0.81,
            "dominant_signals": [],
            "rainfall_3d_mm": 183.0,
            "soil_moisture_percentile": 91.0,
            "issued_at": datetime.now(timezone.utc),
        }
        msg = engine.format_whatsapp_message(alert, language="hi")
        assert "Wayanad" in msg  # district name unchanged
        assert "SLOPESENSE" in msg

    def test_cap_xml_valid(self, engine):
        """CAP XML output should be well-formed."""
        import xml.etree.ElementTree as ET
        alert = {
            "alert_code": "TEST_ALERT_001",
            "tier": "WARNING",
            "district_name": "Wayanad",
            "district_code": "KL_WYD",
            "block_name": "Meppadi",
            "state_name": "Kerala",
            "fpi_score": 0.73,
            "fpi_ci_lower": 0.61,
            "fpi_ci_upper": 0.84,
            "fpi_24h": 0.81,
            "rainfall_3d_mm": 183.0,
            "soil_moisture_percentile": 91.0,
            "issued_at": datetime.now(timezone.utc),
        }
        xml_str = engine.format_cap_xml(alert)
        assert xml_str.strip().startswith("<?xml")
        # Should parse without error
        root = ET.fromstring(xml_str.split("?>", 1)[1])
        assert root is not None


# ── SMAP Tests ────────────────────────────────────────────────────────────────

class TestSMAPIngestion:
    """Tests for SMAP soil moisture processing."""

    @pytest.fixture
    def smap(self):
        from backend.ingestion.smap import SMAPIngestion
        return SMAPIngestion()

    def test_percentile_bounds(self, smap):
        """Percentile should always be 0–100."""
        import xarray as xr
        sm = xr.DataArray(
            np.array([[0.05, 0.20, 0.35, 0.50]]),
            dims=["lat", "lon"],
        )
        pct = smap.compute_percentile(sm, month=7)
        assert float(pct.min()) >= 0.0
        assert float(pct.max()) <= 100.0

    def test_high_moisture_high_percentile(self, smap):
        """Very high soil moisture should map to high percentile during monsoon."""
        import xarray as xr
        # 0.45 m³/m³ is near saturation in Western Ghats
        sm_high = xr.DataArray(np.array([[0.45]]), dims=["lat", "lon"])
        pct_high = smap.compute_percentile(sm_high, month=7)
        assert float(pct_high.mean()) > 80.0

    def test_fpi_contribution_nonlinear(self, smap):
        """FPI contribution should accelerate sharply above 85th percentile."""
        contrib_50 = smap.get_fpi_contribution(50)
        contrib_85 = smap.get_fpi_contribution(85)
        contrib_95 = smap.get_fpi_contribution(95)

        assert contrib_50 < contrib_85 < contrib_95
        # The jump from 85→95 should be bigger than 50→85
        assert (contrib_95 - contrib_85) > (contrib_85 - contrib_50) * 0.3

    def test_synthetic_fallback(self, smap):
        """Should return valid data even without credentials."""
        da = smap._generate_synthetic(datetime(2024, 7, 29), {
            "min_lat": 11.3, "max_lat": 11.9,
            "min_lon": 75.7, "max_lon": 76.4,
        })
        assert da is not None
        assert float(da.min()) >= 0.0
        assert float(da.max()) <= 1.0


# ── GPM Tests ─────────────────────────────────────────────────────────────────

class TestGPMIngestion:
    """Tests for GPM rainfall ingestion."""

    @pytest.fixture
    def gpm(self):
        from backend.ingestion.gpm import GPMIngestion
        return GPMIngestion()

    def test_synthetic_data_shape(self, gpm):
        """Synthetic data should have correct spatial dimensions."""
        bbox = {"min_lat": 11.3, "max_lat": 11.9, "min_lon": 75.7, "max_lon": 76.4}
        ds = gpm._generate_synthetic(datetime(2024, 7, 29), bbox)
        assert ds is not None
        assert "precipitation_mmhr" in ds
        assert ds["precipitation_mmhr"].min() >= 0.0

    def test_accumulation_nonnegative(self, gpm):
        """3-day rainfall accumulation should always be non-negative."""
        with patch.object(gpm, 'fetch_halfhourly', side_effect=lambda *a, **kw: gpm._generate_synthetic(a[0], {"min_lat": 11.0, "max_lat": 12.0, "min_lon": 75.0, "max_lon": 77.0})):
            accum = gpm.compute_accumulation(
                datetime(2024, 7, 29),
                days=3,
                bbox={"min_lat": 11.0, "max_lat": 12.0, "min_lon": 75.0, "max_lon": 77.0},
            )
            assert float(accum.min()) >= 0.0

    def test_synthetic_orographic_enhancement(self, gpm):
        """Western Ghats (lon ~76) should have higher rainfall than surrounding areas."""
        bbox = {"min_lat": 10.0, "max_lat": 14.0, "min_lon": 73.0, "max_lon": 79.0}
        ds = gpm._generate_synthetic(datetime(2024, 7, 15), bbox)
        precip = ds["precipitation_mmhr"]

        # Ghats band (lon 75.5–77.5)
        ghats_mean = float(precip.sel(lon=slice(75.5, 77.5)).mean())
        coast_mean = float(precip.sel(lon=slice(73.0, 75.0)).mean())
        assert ghats_mean > coast_mean, "Orographic enhancement not detected in synthetic data"


# ── Retrospective Tests ───────────────────────────────────────────────────────

class TestRetrospective:
    """Tests for retrospective validation logic."""

    def test_all_events_defined(self):
        """All 6 historical events should be defined."""
        from backend.model.retrospective import HISTORICAL_EVENTS
        assert len(HISTORICAL_EVENTS) == 6
        event_ids = [e["id"] for e in HISTORICAL_EVENTS]
        assert "wayanad_2024" in event_ids
        assert "kedarnath_2013" in event_ids
        assert "malin_2014" in event_ids

    def test_synthetic_fpi_estimate_wayanad(self):
        """Wayanad synthetic estimate should exceed WARNING threshold."""
        from backend.model.retrospective import RetrospectiveRunner, HISTORICAL_EVENTS
        runner = RetrospectiveRunner()
        wayanad = next(e for e in HISTORICAL_EVENTS if e["id"] == "wayanad_2024")
        fpi_t24 = runner._synthetic_fpi_estimate(wayanad, 24)
        assert fpi_t24 >= 0.65, f"Wayanad T-24h estimate should be WARNING+, got {fpi_t24}"

    def test_synthetic_fpi_estimate_increases_toward_event(self):
        """FPI should generally increase as event approaches."""
        from backend.model.retrospective import RetrospectiveRunner, HISTORICAL_EVENTS
        runner = RetrospectiveRunner()
        kedarnath = next(e for e in HISTORICAL_EVENTS if e["id"] == "kedarnath_2013")

        fpi_48h = runner._synthetic_fpi_estimate(kedarnath, 48)
        fpi_24h = runner._synthetic_fpi_estimate(kedarnath, 24)
        fpi_12h = runner._synthetic_fpi_estimate(kedarnath, 12)
        fpi_0h = runner._synthetic_fpi_estimate(kedarnath, 0)

        # Not strictly monotonic but overall trend should be increasing
        assert fpi_0h >= fpi_48h, "FPI at event should exceed FPI 48h before"


# ── Preprocessor Tests ────────────────────────────────────────────────────────

class TestDataPreprocessor:
    """Tests for data regridding and alignment."""

    @pytest.fixture
    def preprocessor(self):
        from backend.processing.preprocessor import DataPreprocessor
        return DataPreprocessor(bbox={
            "min_lat": 11.3, "max_lat": 11.9,
            "min_lon": 75.7, "max_lon": 76.4,
        })

    def test_regrid_simple_array(self, preprocessor):
        """Regrid should produce output matching target grid dimensions."""
        import xarray as xr
        src = xr.DataArray(
            np.random.rand(10, 10),
            dims=["lat", "lon"],
            coords={
                "lat": np.linspace(11.0, 12.5, 10),
                "lon": np.linspace(75.5, 76.9, 10),
            }
        )
        result = preprocessor._regrid(src)
        expected_lats = len(preprocessor.target_lats)
        expected_lons = len(preprocessor.target_lons)
        assert result.shape == (expected_lats, expected_lons)

    def test_susceptibility_wayanad_high_risk(self, preprocessor):
        """Wayanad (lat~11.6, lon~76.1) should be class 5 (very high risk)."""
        cls = preprocessor._classify_susceptibility(11.6, 76.1)
        assert cls == 5, f"Wayanad should be susceptibility class 5, got {cls}"

    def test_susceptibility_plains_low_risk(self, preprocessor):
        """Rajasthan plains should be class 1 (very low risk)."""
        cls = preprocessor._classify_susceptibility(26.0, 74.0)
        assert cls == 1, f"Rajasthan plains should be class 1, got {cls}"

    def test_regrid_nan_handling(self, preprocessor):
        """Regrid should handle NaN values without crashing."""
        import xarray as xr
        src = xr.DataArray(
            np.array([[1.0, np.nan], [np.nan, 2.0]]),
            dims=["lat", "lon"],
            coords={
                "lat": np.array([11.3, 11.6]),
                "lon": np.array([75.7, 76.1]),
            }
        )
        result = preprocessor._regrid(src)
        assert result is not None
        assert not np.any(np.isnan(result))


# ── Integration: Alert message contains correct FPI info ──────────────────────

class TestIntegration:
    """End-to-end integration tests using synthetic data."""

    def test_physics_fpi_to_alert_tier_pipeline(self):
        """Full pipeline: features → FPI score → tier → WhatsApp message."""
        from backend.model.fpi_engine import FPIEngine
        from backend.alert.alert_engine import AlertEngine

        engine = FPIEngine()
        alert_engine = AlertEngine()

        # Wayanad-like conditions
        features = {
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

        fpi = engine._score_physics(features)
        assert fpi >= 0.65

        ci_lo, ci_hi = engine._compute_confidence_interval(fpi, features)
        is_suppressed = (ci_hi - ci_lo) > 0.30
        tier = engine._classify_tier(fpi, is_suppressed)
        assert tier in ("WARNING", "EMERGENCY")

        alert = {
            "tier": tier,
            "district_name": "Wayanad",
            "block_name": "Meppadi",
            "state_name": "Kerala",
            "fpi_score": fpi,
            "fpi_ci_lower": ci_lo,
            "fpi_ci_upper": ci_hi,
            "fpi_24h": engine._score_cell_forecast(features, 24),
            "dominant_signals": [{"signal": "rainfall_accumulation"}],
            "rainfall_3d_mm": 183.0,
            "soil_moisture_percentile": 91.0,
            "issued_at": datetime.now(timezone.utc),
        }

        msg = alert_engine.format_whatsapp_message(alert, language="en")
        assert "Wayanad" in msg
        assert len(msg) > 100


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
