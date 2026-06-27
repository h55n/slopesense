"""
SlopeSense — White-box tests for Risk Label functions.

Tests every function added to fpi_engine.py:
  - get_risk_level(), get_risk_label(), get_risk_description()
  - get_risk_action(), get_risk_color(), get_risk_short()

Covers: boundary values, edge cases, monotonicity, completeness.
"""

import pytest
from backend.model.fpi_engine import (
    get_risk_level,
    get_risk_label,
    get_risk_description,
    get_risk_action,
    get_risk_color,
    get_risk_short,
    RISK_LEVELS,
)


class TestRiskLevelMapping:
    """White-box: correct tier returned at every FPI boundary."""

    def test_critical_at_0_80(self):
        assert get_risk_label(0.80) == "CRITICAL"

    def test_critical_above_0_80(self):
        assert get_risk_label(0.95) == "CRITICAL"
        assert get_risk_label(1.00) == "CRITICAL"

    def test_high_at_0_65(self):
        assert get_risk_label(0.65) == "HIGH"

    def test_high_between_0_65_and_0_79(self):
        assert get_risk_label(0.70) == "HIGH"
        assert get_risk_label(0.79) == "HIGH"

    def test_elevated_at_0_40(self):
        assert get_risk_label(0.40) == "ELEVATED"

    def test_elevated_between_0_40_and_0_64(self):
        assert get_risk_label(0.50) == "ELEVATED"
        assert get_risk_label(0.64) == "ELEVATED"

    def test_moderate_at_0_20(self):
        assert get_risk_label(0.20) == "MODERATE"

    def test_moderate_between_0_20_and_0_39(self):
        assert get_risk_label(0.25) == "MODERATE"
        assert get_risk_label(0.39) == "MODERATE"

    def test_low_below_0_20(self):
        assert get_risk_label(0.19) == "LOW"
        assert get_risk_label(0.10) == "LOW"
        assert get_risk_label(0.0) == "LOW"

    def test_five_tiers_total(self):
        """Exactly 5 tiers, no more, no less."""
        labels = set()
        for fpi in [0.0, 0.19, 0.20, 0.39, 0.40, 0.64, 0.65, 0.79, 0.80, 1.0]:
            labels.add(get_risk_label(fpi))
        assert labels == {"LOW", "MODERATE", "ELEVATED", "HIGH", "CRITICAL"}


class TestRiskLevelHelpers:
    """White-box: each helper returns correct type and value."""

    def test_get_risk_level_returns_dict(self):
        result = get_risk_level(0.75)
        assert isinstance(result, dict)
        assert "label" in result
        assert "description" in result
        assert "color" in result
        assert "emoji" in result

    def test_get_risk_description_is_nonempty(self):
        for fpi in [0.0, 0.25, 0.50, 0.75, 0.90]:
            desc = get_risk_description(fpi)
            assert isinstance(desc, str)
            assert len(desc) > 20, f"Description too short for FPI={fpi}"

    def test_get_risk_action_is_nonempty(self):
        for fpi in [0.0, 0.25, 0.50, 0.75, 0.90]:
            action = get_risk_action(fpi)
            assert isinstance(action, str)
            assert len(action) > 10, f"Action too short for FPI={fpi}"

    def test_get_risk_color_is_hex(self):
        for fpi in [0.0, 0.25, 0.50, 0.75, 0.90]:
            color = get_risk_color(fpi)
            assert color.startswith("#"), f"Color not hex for FPI={fpi}"
            assert len(color) == 7, f"Color not 6-digit hex for FPI={fpi}"

    def test_get_risk_short_is_nonempty(self):
        for fpi in [0.0, 0.25, 0.50, 0.75, 0.90]:
            short = get_risk_short(fpi)
            assert isinstance(short, str)
            assert len(short) > 3


class TestRiskColorSemantics:
    """White-box: colors are semantically correct (safe=green, danger=red)."""

    def test_critical_is_red(self):
        color = get_risk_color(0.85)
        # Should be a red color (hex starts with high red component)
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        assert r > 180, f"CRITICAL should be red-dominant, got {color}"
        assert r > g, "Red channel should dominate for CRITICAL"

    def test_low_is_green(self):
        color = get_risk_color(0.05)
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        assert g > r, f"LOW should be green-dominant, got {color}"
        assert g > 150, f"LOW should be distinctly green, got {color}"

    def test_colors_are_different_per_tier(self):
        colors = [get_risk_color(fpi) for fpi in [0.05, 0.25, 0.50, 0.70, 0.90]]
        assert len(set(colors)) == 5, "Each risk level should have a unique color"


class TestRiskLevelsDataIntegrity:
    """White-box: the RISK_LEVELS constant itself is well-formed."""

    def test_risk_levels_ordered_descending(self):
        """min_fpi values must be strictly decreasing."""
        fpis = [level["min_fpi"] for level in RISK_LEVELS]
        assert fpis == sorted(fpis, reverse=True), "RISK_LEVELS must be ordered high→low FPI"

    def test_lowest_level_has_min_fpi_zero(self):
        assert RISK_LEVELS[-1]["min_fpi"] == 0.0, "Last level must start at 0.0 to catch all scores"

    def test_all_required_keys_present(self):
        required = {"min_fpi", "label", "short", "description", "action", "color", "bg_color", "emoji"}
        for level in RISK_LEVELS:
            missing = required - set(level.keys())
            assert not missing, f"Level {level.get('label')} missing keys: {missing}"

    def test_no_duplicate_labels(self):
        labels = [level["label"] for level in RISK_LEVELS]
        assert len(labels) == len(set(labels)), "Duplicate labels in RISK_LEVELS"

    def test_all_emojis_nonempty(self):
        for level in RISK_LEVELS:
            assert level["emoji"], f"Level {level['label']} has empty emoji"


class TestFPIEdgeCases:
    """White-box: edge cases that could break the system."""

    def test_exactly_at_boundary_0_80(self):
        """FPI=0.80 must return CRITICAL not HIGH."""
        assert get_risk_label(0.80) == "CRITICAL"

    def test_just_below_boundary_0_80(self):
        """FPI=0.799... must return HIGH."""
        assert get_risk_label(0.7999) == "HIGH"

    def test_exactly_at_boundary_0_65(self):
        assert get_risk_label(0.65) == "HIGH"

    def test_just_below_boundary_0_65(self):
        assert get_risk_label(0.6499) == "ELEVATED"

    def test_exactly_at_boundary_0_40(self):
        assert get_risk_label(0.40) == "ELEVATED"

    def test_exactly_at_boundary_0_20(self):
        assert get_risk_label(0.20) == "MODERATE"

    def test_zero_fpi(self):
        assert get_risk_label(0.0) == "LOW"

    def test_near_zero_fpi(self):
        assert get_risk_label(0.001) == "LOW"

    def test_fpi_unity(self):
        """FPI=1.0 (maximum) must return CRITICAL."""
        assert get_risk_label(1.0) == "CRITICAL"
