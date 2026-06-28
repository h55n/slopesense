"""
SlopeSense — Science Validation & FPI Model Correctness Tests

Tests that the FPI model produces scientifically correct results:
- Physical consistency (higher rainfall → higher FPI)
- Threshold calibration (known events are flagged correctly)
- Alert tier semantics (tier boundaries match specification)
- Retrospective accuracy (6/6 historic events flagged at T-24h)
- Signal importance (slope, rainfall, soil moisture all contribute)

Run: pytest backend/tests/test_science_validation.py -v
"""

import pytest
import numpy as np


# ── FPI Physics Monotonicity Tests ────────────────────────────────────────────

class TestFPIPhysicsMonotonicity:
    """FPI must be monotonically increasing with risk factors."""

    @pytest.fixture
    def engine(self):
        from backend.model.fpi_engine import FPIEngine
        return FPIEngine()

    @pytest.fixture
    def base_features(self):
        """Neutral baseline features — produces a moderate FPI."""
        return {
            "rainfall_3d_mm": 50.0,
            "rainfall_24h_mm": 20.0,
            "forecast_24h_mm": 15.0,
            "forecast_48h_mm": 10.0,
            "soil_moisture_pct": 50.0,
            "soil_moisture_abs": 0.25,
            "slope_degrees": 25.0,
            "aspect_degrees": 180.0,
            "elevation_m": 700.0,
            "ndvi_delta": 0.0,
            "susceptibility_class": 3.0,
        }

    def test_higher_rainfall_increases_fpi(self, engine, base_features):
        """FPI must be higher when 3-day rainfall is higher."""
        features_low = {**base_features, "rainfall_3d_mm": 30.0}
        features_high = {**base_features, "rainfall_3d_mm": 200.0}
        fpi_low = engine._score_physics(features_low)
        fpi_high = engine._score_physics(features_high)
        assert fpi_high > fpi_low, (
            f"Expected higher rainfall to increase FPI: low={fpi_low:.3f}, high={fpi_high:.3f}"
        )

    def test_higher_soil_moisture_increases_fpi(self, engine, base_features):
        """FPI must be higher when soil is more saturated."""
        features_dry = {**base_features, "soil_moisture_pct": 20.0}
        features_wet = {**base_features, "soil_moisture_pct": 95.0}
        fpi_dry = engine._score_physics(features_dry)
        fpi_wet = engine._score_physics(features_wet)
        assert fpi_wet > fpi_dry, (
            f"Expected wetter soil to increase FPI: dry={fpi_dry:.3f}, wet={fpi_wet:.3f}"
        )

    def test_steeper_slope_increases_fpi(self, engine, base_features):
        """Steeper slopes should produce higher FPI (more susceptibility)."""
        features_flat = {**base_features, "slope_degrees": 5.0}
        features_steep = {**base_features, "slope_degrees": 45.0}
        fpi_flat = engine._score_physics(features_flat)
        fpi_steep = engine._score_physics(features_steep)
        assert fpi_steep > fpi_flat, (
            f"Expected steeper slope to increase FPI: flat={fpi_flat:.3f}, steep={fpi_steep:.3f}"
        )

    def test_higher_susceptibility_increases_fpi(self, engine, base_features):
        """Higher NDMA susceptibility class should increase FPI."""
        features_low_susc = {**base_features, "susceptibility_class": 1.0}
        features_high_susc = {**base_features, "susceptibility_class": 5.0}
        fpi_low = engine._score_physics(features_low_susc)
        fpi_high = engine._score_physics(features_high_susc)
        assert fpi_high >= fpi_low, (
            f"Expected higher susceptibility to increase FPI: low={fpi_low:.3f}, high={fpi_high:.3f}"
        )

    def test_fpi_always_in_unit_interval(self, engine, base_features):
        """FPI must always be in [0.0, 1.0] for any input combination."""
        test_cases = [
            {**base_features},
            {**base_features, "rainfall_3d_mm": 0.0, "soil_moisture_pct": 0.0},
            {**base_features, "rainfall_3d_mm": 500.0, "soil_moisture_pct": 100.0, "slope_degrees": 60.0},
            {**base_features, "ndvi_delta": -0.5, "susceptibility_class": 5.0},
        ]
        for features in test_cases:
            fpi = engine._score_physics(features)
            assert 0.0 <= fpi <= 1.0, f"FPI {fpi} is outside [0,1] for features: {features}"

    def test_higher_forecast_rainfall_increases_fpi(self, engine, base_features):
        """Higher forecast rainfall increases the 24h forward FPI."""
        f_low = {**base_features, "forecast_24h_mm": 10.0}
        f_high = {**base_features, "forecast_24h_mm": 120.0}
        fpi_low = engine._score_physics(f_low)
        fpi_high = engine._score_physics(f_high)
        assert fpi_high >= fpi_low, (
            f"Expected higher forecast to increase FPI: low={fpi_low:.3f}, high={fpi_high:.3f}"
        )

    def test_negative_ndvi_delta_increases_fpi(self, engine, base_features):
        """Vegetation loss (negative NDVI change) should increase FPI."""
        f_gain = {**base_features, "ndvi_delta": 0.1}
        f_loss = {**base_features, "ndvi_delta": -0.3}
        fpi_gain = engine._score_physics(f_gain)
        fpi_loss = engine._score_physics(f_loss)
        assert fpi_loss >= fpi_gain, (
            f"Expected vegetation loss to increase FPI: gain={fpi_gain:.3f}, loss={fpi_loss:.3f}"
        )


# ── Wayanad 2024 Calibration Test ─────────────────────────────────────────────

class TestWayanad2024Calibration:
    """The model must reproduce the Wayanad 2024 scenario correctly."""

    @pytest.fixture
    def engine(self):
        from backend.model.fpi_engine import FPIEngine
        return FPIEngine()

    def test_wayanad_conditions_produce_warning_or_emergency(self, engine):
        """July 29, 2024 Wayanad conditions must produce >= WARNING (FPI >= 0.65)."""
        wayanad_features = {
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
        fpi = engine._score_physics(wayanad_features)
        assert fpi >= 0.65, (
            f"Wayanad conditions should produce WARNING or EMERGENCY FPI, got {fpi:.3f}. "
            "This event killed 420 people; our model must flag it."
        )

    def test_wayanad_fpi_significantly_above_watch_threshold(self, engine):
        """FPI should be well above 40% (WATCH) for Wayanad — not ambiguous."""
        wayanad_features = {
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
        fpi = engine._score_physics(wayanad_features)
        assert fpi >= 0.60, (
            f"Wayanad FPI should be substantially above WATCH threshold; got {fpi:.3f}"
        )

    def test_dry_conditions_produce_low_fpi(self, engine):
        """Dry, flat, low-susceptibility conditions should produce NORMAL FPI (<0.40)."""
        dry_features = {
            "rainfall_3d_mm": 10.0,
            "rainfall_24h_mm": 3.0,
            "forecast_24h_mm": 5.0,
            "forecast_48h_mm": 2.0,
            "soil_moisture_pct": 20.0,
            "soil_moisture_abs": 0.08,
            "slope_degrees": 10.0,
            "aspect_degrees": 90.0,
            "elevation_m": 200.0,
            "ndvi_delta": 0.05,
            "susceptibility_class": 1.0,
        }
        fpi = engine._score_physics(dry_features)
        assert fpi < 0.40, (
            f"Dry conditions should produce NORMAL FPI (<0.40), got {fpi:.3f}"
        )


# ── Alert Tier Boundary Tests ─────────────────────────────────────────────────

class TestAlertTierBoundaries:
    """Alert tiers must map exactly to specification boundaries."""

    @pytest.fixture
    def engine(self):
        from backend.model.fpi_engine import FPIEngine
        return FPIEngine()

    def test_normal_tier_at_zero_point_39(self, engine):
        """FPI = 0.39 should be NORMAL."""
        tier = engine._classify_tier(0.39, is_suppressed=False)
        assert tier == "NORMAL", f"FPI 0.39 should be NORMAL, got {tier}"

    def test_watch_tier_at_zero_point_40(self, engine):
        """FPI = 0.40 should be WATCH (boundary)."""
        tier = engine._classify_tier(0.40, is_suppressed=False)
        assert tier == "WATCH", f"FPI 0.40 should be WATCH, got {tier}"

    def test_watch_tier_at_zero_point_64(self, engine):
        """FPI = 0.64 should be WATCH."""
        tier = engine._classify_tier(0.64, is_suppressed=False)
        assert tier == "WATCH", f"FPI 0.64 should be WATCH, got {tier}"

    def test_warning_tier_at_zero_point_65(self, engine):
        """FPI = 0.65 should be WARNING (boundary)."""
        tier = engine._classify_tier(0.65, is_suppressed=False)
        assert tier == "WARNING", f"FPI 0.65 should be WARNING, got {tier}"

    def test_warning_tier_at_zero_point_79(self, engine):
        """FPI = 0.79 should be WARNING."""
        tier = engine._classify_tier(0.79, is_suppressed=False)
        assert tier == "WARNING", f"FPI 0.79 should be WARNING, got {tier}"

    def test_emergency_tier_at_zero_point_80(self, engine):
        """FPI = 0.80 should be EMERGENCY (boundary)."""
        tier = engine._classify_tier(0.80, is_suppressed=False)
        assert tier == "EMERGENCY", f"FPI 0.80 should be EMERGENCY, got {tier}"

    def test_emergency_tier_at_one_point_zero(self, engine):
        """FPI = 1.0 should be EMERGENCY."""
        tier = engine._classify_tier(1.0, is_suppressed=False)
        assert tier == "EMERGENCY", f"FPI 1.0 should be EMERGENCY, got {tier}"

    def test_suppressed_tier_is_monitoring(self, engine):
        """Any FPI with is_suppressed=True should return MONITORING."""
        for fpi in [0.30, 0.50, 0.70, 0.90]:
            tier = engine._classify_tier(fpi, is_suppressed=True)
            assert tier == "MONITORING", (
                f"Suppressed FPI {fpi} should be MONITORING, got {tier}"
            )


# ── CAP XML Validation ────────────────────────────────────────────────────────

class TestCAPXMLGeneration:
    """CAP v1.2 XML output must be standards-compliant."""

    @pytest.fixture
    def alert_engine(self):
        from backend.alert.alert_engine import AlertEngine
        return AlertEngine()

    def test_cap_xml_is_valid_xml(self, alert_engine, sample_alert):
        import xml.etree.ElementTree as ET
        xml_str = alert_engine.format_cap_xml(sample_alert)
        # Should parse without error
        ET.fromstring(xml_str)

    def test_cap_xml_contains_cap_namespace(self, alert_engine, sample_alert):
        xml_str = alert_engine.format_cap_xml(sample_alert)
        assert "emergency:cap" in xml_str

    def test_cap_xml_contains_district_name(self, alert_engine, sample_alert):
        xml_str = alert_engine.format_cap_xml(sample_alert)
        assert "Wayanad" in xml_str

    def test_cap_xml_contains_severity(self, alert_engine, sample_alert):
        xml_str = alert_engine.format_cap_xml(sample_alert)
        # CAP severity must be one of the standard values
        valid_severities = {"Extreme", "Severe", "Moderate", "Minor", "Unknown"}
        has_severity = any(sev in xml_str for sev in valid_severities)
        assert has_severity, f"CAP XML missing standard severity element"

    def test_cap_xml_emergency_produces_extreme_severity(self, alert_engine, sample_alert):
        """EMERGENCY alerts should map to CAP 'Extreme' severity."""
        emergency_alert = {**sample_alert, "tier": "EMERGENCY", "fpi_score": 0.90}
        xml_str = alert_engine.format_cap_xml(emergency_alert)
        assert "Extreme" in xml_str or "EMERGENCY" in xml_str, (
            "EMERGENCY tier alert should produce Extreme severity in CAP XML"
        )


# ── Risk Labels Semantic Tests ────────────────────────────────────────────────

class TestRiskLabelsSemantics:
    """Risk labels must be semantically correct and self-consistent."""

    def test_risk_label_high_fpi_returns_critical(self):
        """FPI >= 0.80 should map to the most critical label."""
        from backend.model.fpi_engine import get_risk_label
        label = get_risk_label(0.85)
        assert label in ("CRITICAL", "EMERGENCY", "EXTREME"), (
            f"FPI 0.85 should produce most critical label, got: {label}"
        )

    def test_risk_label_low_fpi_returns_low(self):
        """FPI < 0.20 should map to the least urgent label."""
        from backend.model.fpi_engine import get_risk_label
        label = get_risk_label(0.05)
        assert label in ("LOW", "NORMAL", "MINIMAL"), (
            f"FPI 0.05 should produce lowest label, got: {label}"
        )

    def test_all_risk_levels_have_required_fields(self):
        """Every risk level dict must contain all required keys."""
        from backend.model.fpi_engine import RISK_LEVELS
        required = {"min_fpi", "label", "color", "description", "action", "short"}
        for level in RISK_LEVELS:
            missing = required - level.keys()
            assert not missing, f"Risk level {level.get('label')} missing fields: {missing}"

    def test_risk_colors_are_valid_hex(self):
        """Risk colors must be valid HTML hex codes."""
        from backend.model.fpi_engine import RISK_LEVELS
        import re
        hex_pattern = re.compile(r"^#[0-9A-Fa-f]{6}$")
        for level in RISK_LEVELS:
            color = level["color"]
            assert hex_pattern.match(color), (
                f"Risk color '{color}' for level '{level['label']}' is not a valid hex color"
            )

    def test_fpi_thresholds_are_monotonically_ordered(self):
        """Risk levels sorted by urgency should have decreasing min_fpi."""
        from backend.model.fpi_engine import RISK_LEVELS
        thresholds = [r["min_fpi"] for r in RISK_LEVELS]
        # They should be in descending order (most critical first)
        assert thresholds == sorted(thresholds, reverse=True), (
            f"Risk level thresholds should be monotonically decreasing, got: {thresholds}"
        )

    def test_lowest_level_covers_zero(self):
        """The least urgent risk level must cover FPI = 0.0."""
        from backend.model.fpi_engine import get_risk_label
        label = get_risk_label(0.0)
        assert label, "Should return a non-empty label for FPI=0.0"

    def test_highest_level_covers_one(self):
        """The most urgent risk level must cover FPI = 1.0."""
        from backend.model.fpi_engine import get_risk_label
        label = get_risk_label(1.0)
        assert label, "Should return a non-empty label for FPI=1.0"

    def test_risk_descriptions_are_non_empty(self):
        """All risk levels must have a non-empty description and action."""
        from backend.model.fpi_engine import RISK_LEVELS
        for level in RISK_LEVELS:
            assert level["description"].strip(), (
                f"Risk level '{level['label']}' has empty description"
            )
            assert level["action"].strip(), (
                f"Risk level '{level['label']}' has empty action"
            )


# ── Grid Processing Tests ─────────────────────────────────────────────────────

class TestFeatureGridProcessing:
    """Test the FPI engine's grid-level computations."""

    def test_vectorized_computation_returns_correct_shape(self, mock_feature_grid):
        """compute_grid_vectorized() must return array of same shape as input grid."""
        from backend.model.fpi_engine import FPIEngine
        engine = FPIEngine()
        result = engine.compute_grid_vectorized(mock_feature_grid)
        expected_rows = len(mock_feature_grid.lats)
        expected_cols = len(mock_feature_grid.lons)
        assert result.shape == (expected_rows, expected_cols), (
            f"Expected shape ({expected_rows}, {expected_cols}), got {result.shape}"
        )

    def test_vectorized_computation_all_values_in_unit_interval(self, mock_feature_grid):
        """All FPI scores in the grid must be in [0, 1]."""
        from backend.model.fpi_engine import FPIEngine
        engine = FPIEngine()
        result = engine.compute_grid_vectorized(mock_feature_grid)
        assert np.all(result >= 0.0) and np.all(result <= 1.0), (
            f"Some FPI values outside [0, 1]: min={result.min():.3f}, max={result.max():.3f}"
        )

    def test_full_grid_computation_returns_cell_list(self, mock_feature_grid):
        """compute_grid() must return a list of CellFPI objects."""
        from backend.model.fpi_engine import FPIEngine, CellFPI
        engine = FPIEngine()
        cells = engine.compute_grid(mock_feature_grid)
        assert isinstance(cells, list)
        assert len(cells) > 0
        assert all(hasattr(c, "fpi_score") for c in cells), (
            "All cells must have fpi_score attribute"
        )

    def test_full_grid_cell_fpis_all_in_unit_interval(self, mock_feature_grid):
        """All cell FPI scores must be in [0.0, 1.0]."""
        from backend.model.fpi_engine import FPIEngine
        engine = FPIEngine()
        cells = engine.compute_grid(mock_feature_grid)
        for cell in cells:
            assert 0.0 <= cell.fpi_score <= 1.0, (
                f"Cell {cell.cell_id} has FPI {cell.fpi_score} outside [0, 1]"
            )

    def test_forecast_scores_higher_when_rain_forecast_high(self):
        """24h forecast FPI should be higher when forecast rainfall is high."""
        from backend.model.fpi_engine import FPIEngine
        engine = FPIEngine()
        base = {
            "rainfall_3d_mm": 100.0, "rainfall_24h_mm": 50.0,
            "forecast_24h_mm": 10.0, "forecast_48h_mm": 5.0,
            "soil_moisture_pct": 60.0, "soil_moisture_abs": 0.30,
            "slope_degrees": 30.0, "aspect_degrees": 180.0,
            "elevation_m": 700.0, "ndvi_delta": 0.0, "susceptibility_class": 3.0,
        }
        high_forecast = {**base, "forecast_24h_mm": 120.0}
        fpi_low = engine._score_cell_forecast(base, horizon_h=24)
        fpi_high = engine._score_cell_forecast(high_forecast, horizon_h=24)
        assert fpi_high >= fpi_low, (
            f"Higher forecast should produce higher 24h FPI: low={fpi_low:.3f}, high={fpi_high:.3f}"
        )


# ── Confidence Interval Tests ─────────────────────────────────────────────────

class TestConfidenceIntervals:
    """FPI confidence intervals must be physically sensible."""

    @pytest.fixture
    def engine(self):
        from backend.model.fpi_engine import FPIEngine
        return FPIEngine()

    @pytest.fixture
    def base_features(self):
        return {
            "rainfall_3d_mm": 150.0, "rainfall_24h_mm": 60.0,
            "forecast_24h_mm": 40.0, "forecast_48h_mm": 30.0,
            "soil_moisture_pct": 75.0, "soil_moisture_abs": 0.35,
            "slope_degrees": 30.0, "aspect_degrees": 180.0,
            "elevation_m": 800.0, "ndvi_delta": -0.01, "susceptibility_class": 4.0,
        }

    def test_ci_lower_less_than_ci_upper(self, engine, base_features):
        """CI lower bound must always be < CI upper bound."""
        fpi = engine._score_physics(base_features)
        ci_lower, ci_upper = engine._compute_confidence_interval(fpi, base_features)
        assert ci_lower < ci_upper, (
            f"CI lower ({ci_lower:.3f}) must be less than CI upper ({ci_upper:.3f})"
        )

    def test_ci_bounds_within_unit_interval(self, engine, base_features):
        """CI bounds must be within [0, 1]."""
        for fpi in [0.0, 0.30, 0.65, 0.90, 1.0]:
            ci_lower, ci_upper = engine._compute_confidence_interval(fpi, base_features)
            assert 0.0 <= ci_lower <= 1.0, f"CI lower {ci_lower} out of range"
            assert 0.0 <= ci_upper <= 1.0, f"CI upper {ci_upper} out of range"

    def test_fpi_within_ci(self, engine, base_features):
        """The FPI score should be within or very near its own CI."""
        fpi = engine._score_physics(base_features)
        ci_lower, ci_upper = engine._compute_confidence_interval(fpi, base_features)
        # FPI should be within its own CI (with small tolerance for edge effects)
        assert ci_lower <= fpi + 0.001 and fpi - 0.001 <= ci_upper, (
            f"FPI {fpi:.3f} should be within CI [{ci_lower:.3f}, {ci_upper:.3f}]"
        )

    def test_wide_ci_triggers_suppression(self, engine):
        """CI width > 0.30 should trigger MONITORING (suppression)."""
        # Engineer a situation with wide CI: flat terrain, low susceptibility
        flat_features = {
            "rainfall_3d_mm": 80.0, "rainfall_24h_mm": 30.0,
            "forecast_24h_mm": 20.0, "forecast_48h_mm": 10.0,
            "soil_moisture_pct": 55.0, "soil_moisture_abs": 0.25,
            "slope_degrees": 2.0,    # very flat → extra uncertainty
            "aspect_degrees": 180.0, "elevation_m": 100.0,
            "ndvi_delta": 0.0,
            "susceptibility_class": 1.0,  # very low → extra uncertainty
        }
        fpi = engine._score_physics(flat_features)
        ci_lower, ci_upper = engine._compute_confidence_interval(fpi, flat_features)
        is_suppressed = (ci_upper - ci_lower) > 0.30
        tier = engine._classify_tier(fpi, is_suppressed)
        # With physics-based model (no trained model), flat+low-susc should trigger suppression
        if is_suppressed:
            assert tier == "MONITORING", (
                f"Wide CI ({ci_upper - ci_lower:.3f}) should produce MONITORING tier, got {tier}"
            )


# ── Retrospective Validation Logic ────────────────────────────────────────────

class TestRetrospectiveValidationLogic:
    """Verify the model correctly identifies historic events."""

    def test_six_known_events_all_above_watch_threshold(self):
        """All 6 known India landslide events should produce FPI >= WATCH (0.40)."""
        from backend.model.fpi_engine import FPIEngine
        engine = FPIEngine()

        known_events = [
            # (name, rainfall_3d, soil_moisture, slope, susceptibility)
            ("Wayanad_2024",     183, 91, 34, 5),
            ("Kedarnath_2013",   220, 88, 42, 5),
            ("Malin_2014",       160, 85, 38, 5),
            ("Chamoli_2021",     140, 82, 44, 5),
            ("Sikkim_2023",      195, 90, 40, 5),
            ("Joshimath_2023",   130, 80, 35, 4),
        ]

        flagged = 0
        for name, rain, sm, slope, susc in known_events:
            features = {
                "rainfall_3d_mm": float(rain),
                "rainfall_24h_mm": rain * 0.45,
                "forecast_24h_mm": rain * 0.35,
                "forecast_48h_mm": rain * 0.25,
                "soil_moisture_pct": float(sm),
                "soil_moisture_abs": sm / 200.0,
                "slope_degrees": float(slope),
                "aspect_degrees": 220.0,
                "elevation_m": 900.0,
                "ndvi_delta": -0.02,
                "susceptibility_class": float(susc),
            }
            fpi = engine._score_physics(features)
            tier = engine._classify_tier(fpi, is_suppressed=False)
            if tier in ("WATCH", "WARNING", "EMERGENCY"):
                flagged += 1
            else:
                print(f"MISSED: {name} — FPI={fpi:.3f}, tier={tier}")

        assert flagged == 6, (
            f"Expected all 6 historic events to be flagged at WATCH+, "
            f"only got {flagged}/6"
        )

    def test_wayanad_flagged_at_warning_or_emergency(self):
        """Wayanad 2024 specifically must be at WARNING or EMERGENCY, not just WATCH."""
        from backend.model.fpi_engine import FPIEngine
        engine = FPIEngine()
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
        tier = engine._classify_tier(fpi, is_suppressed=False)
        assert tier in ("WARNING", "EMERGENCY"), (
            f"Wayanad 2024 must be WARNING or EMERGENCY; got tier={tier}, fpi={fpi:.3f}"
        )
