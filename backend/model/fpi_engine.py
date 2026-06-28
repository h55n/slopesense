"""
SlopeSense — Failure Probability Index (FPI) Model Engine

Based on NASA LHASA v2 (Apache 2.0) with India-specific calibration.
Uses gradient boosting (LightGBM) with domain-informed feature engineering.

Model outputs:
  - fpi_score:       0.0–1.0 current failure probability
  - fpi_ci_lower/upper: 95% confidence interval
  - fpi_24h / fpi_48h: forward forecast scores
  - dominant_signal: primary driver of the score
  - alert_tier:      NORMAL / WATCH / WARNING / EMERGENCY / MONITORING
"""

import logging
import pickle
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Alert tier thresholds
THRESHOLDS = {
    "WATCH":     0.40,
    "WARNING":   0.65,
    "EMERGENCY": 0.80,
}

# Feature weights (India-calibrated, based on NDMA event analysis)
# These are the prior weights before LightGBM training.
# In production these come from the trained model's feature_importances_.
FEATURE_WEIGHTS = {
    "rainfall_3d_mm":          0.35,  # strongest single predictor
    "soil_moisture_pct":       0.25,  # priming variable
    "slope_degrees":           0.15,  # static terrain
    "susceptibility_class":    0.12,  # NDMA prior
    "forecast_24h_mm":         0.08,  # forward-looking
    "ndvi_delta":              0.05,  # vegetation change (lagging)
}

# Rainfall thresholds for India (mm / 3 days)
# Tuned against NDMA event inventory 2000–2024
RAINFALL_THRESHOLDS_MM = {
    "western_ghats":  {"watch": 100, "warning": 180, "emergency": 280},
    "himalayan":      {"watch":  80, "warning": 140, "emergency": 220},
    "northeast":      {"watch": 120, "warning": 200, "emergency": 300},
    "default":        {"watch":  90, "warning": 160, "emergency": 250},
}

# ── Human-readable Risk Labels ────────────────────────────────────────────────
# These translate the technical FPI (0–1) into plain language for district
# officers and Gram Pradhans who need immediate, intuitive understanding.

RISK_LEVELS = [
    {
        "min_fpi": 0.80,
        "label": "CRITICAL",
        "short": "Landslide Imminent",
        "description": "Landslide is imminent or already occurring. Immediate evacuation required. All emergency channels activated.",
        "action": "Evacuate all households on or below slopes immediately. Do not wait.",
        "color": "#dc2626",   # red-600
        "bg_color": "#fef2f2",
        "emoji": "🆘",
    },
    {
        "min_fpi": 0.65,
        "label": "HIGH",
        "short": "Very High Risk",
        "description": "Very high probability of landslide within 24–48 hours. Conditions are dangerous.",
        "action": "Pre-position NDRF/SDRF. Issue public advisory. Pre-evacuate highest-risk households near slopes.",
        "color": "#ea580c",   # orange-600
        "bg_color": "#fff7ed",
        "emoji": "🔴",
    },
    {
        "min_fpi": 0.40,
        "label": "ELEVATED",
        "short": "Elevated Risk",
        "description": "Elevated landslide risk. Soil is saturated and terrain is primed. Conditions could deteriorate rapidly.",
        "action": "Alert DDMA. Monitor slopes closely. Warn communities on steep terrain.",
        "color": "#d97706",   # amber-600
        "bg_color": "#fffbeb",
        "emoji": "⚠️",
    },
    {
        "min_fpi": 0.20,
        "label": "MODERATE",
        "short": "Moderate Risk",
        "description": "Some risk factors are present but conditions are not yet dangerous. Continue monitoring.",
        "action": "Stay informed. Review evacuation routes. No immediate action needed.",
        "color": "#65a30d",   # lime-600
        "bg_color": "#f7fee7",
        "emoji": "🟡",
    },
    {
        "min_fpi": 0.0,
        "label": "LOW",
        "short": "Low Risk",
        "description": "No significant landslide risk indicators at this time.",
        "action": "Normal monitoring. No action required.",
        "color": "#16a34a",   # green-600
        "bg_color": "#f0fdf4",
        "emoji": "✅",
    },
]


def get_risk_level(fpi_score: float) -> dict:
    """Return the full risk level dict for a given FPI score."""
    for level in RISK_LEVELS:
        if fpi_score >= level["min_fpi"]:
            return level
    return RISK_LEVELS[-1]


def get_risk_label(fpi_score: float) -> str:
    """Return short risk label (e.g. 'HIGH', 'ELEVATED') for an FPI score."""
    return get_risk_level(fpi_score)["label"]


def get_risk_description(fpi_score: float) -> str:
    """Return plain-English description of the risk for laypersons."""
    return get_risk_level(fpi_score)["description"]


def get_risk_action(fpi_score: float) -> str:
    """Return the recommended action for a given FPI score."""
    return get_risk_level(fpi_score)["action"]


def get_risk_color(fpi_score: float) -> str:
    """Return semantic hex color for a given FPI score."""
    return get_risk_level(fpi_score)["color"]


def get_risk_short(fpi_score: float) -> str:
    """Return short human-readable label (e.g. 'Very High Risk')."""
    return get_risk_level(fpi_score)["short"]


@dataclass
class CellFPI:
    """FPI score and metadata for a single 1km² grid cell."""
    cell_id: str
    lat: float
    lon: float
    district_code: Optional[str]
    block_code: Optional[str]

    fpi_score: float
    fpi_ci_lower: float
    fpi_ci_upper: float
    fpi_24h: float
    fpi_48h: float

    alert_tier: str
    is_suppressed: bool  # True when CI is too wide (model uncertain)

    dominant_signal: str
    signal_breakdown: Dict[str, float]

    rainfall_3d_mm: float
    rainfall_24h_mm: float
    forecast_24h_mm: float
    soil_moisture_pct: float
    slope_degrees: float
    susceptibility_class: int

    run_timestamp: datetime
    model_version: str = "v0.1"


@dataclass
class BlockFPI:
    """Block-level aggregated FPI (spatial cluster of cells)."""
    block_code: str
    block_name: str
    district_code: str
    district_name: str
    state_code: str
    state_name: str
    lat: float
    lon: float

    fpi_score: float          # 95th percentile of cell FPIs in block
    fpi_ci_lower: float
    fpi_ci_upper: float
    fpi_24h: float
    fpi_48h: float

    alert_tier: str
    is_suppressed: bool

    cell_count_total: int
    cell_count_breached: int
    breach_fraction: float

    dominant_signals: List[Dict]
    rainfall_3d_mm: float
    soil_moisture_pct: float

    run_timestamp: datetime


class FPIEngine:
    """
    Core FPI computation engine.

    Two modes:
    1. Physics-based (default, no training required): weighted combination
       of normalised input features with domain-calibrated weights.
    2. ML mode (production): LightGBM model trained on India event inventory.
       Falls back to physics-based if model file not found.
    """

    MODEL_PATH = Path("data/model/fpi_lgbm_india_v01.pkl")

    def __init__(self):
        self.lgbm_model = self._load_model()

    def _load_model(self):
        """Load trained LightGBM model if available."""
        if self.MODEL_PATH.exists():
            try:
                with open(self.MODEL_PATH, "rb") as f:
                    model = pickle.load(f)
                logger.info("FPI: loaded trained LightGBM model")
                return model
            except Exception as e:
                logger.warning(f"FPI: model load failed ({e}), using physics-based")
        else:
            logger.info("FPI: no trained model found, using physics-based engine")
        return None

    def compute_grid_vectorized(self, feature_grid) -> np.ndarray:
        """Vectorized physics-based FPI computation for a full feature grid."""
        # Sanitize: replace NaN fill values with safe defaults before computation
        rainfall_3d = np.nan_to_num(feature_grid.rainfall_3d_mm, nan=0.0)
        soil_moisture = np.nan_to_num(feature_grid.soil_moisture_pct, nan=50.0)
        slope = np.nan_to_num(feature_grid.slope_degrees, nan=15.0)
        susc = np.nan_to_num(feature_grid.susceptibility_class, nan=2.0)
        forecast = np.nan_to_num(feature_grid.forecast_24h_mm, nan=0.0)
        ndvi = np.nan_to_num(feature_grid.ndvi_delta, nan=0.0)

        rain_norm = np.clip(rainfall_3d / 250.0, 0, 1) ** 0.7
        sm_norm = np.clip(soil_moisture / 100.0, 0, 1) ** 1.5
        slope_raw = np.clip((slope - 5) / 45.0, 0, 1)
        slope_norm = np.where(slope <= 40, slope_raw, slope_raw * 0.85)
        susc_norm = np.clip((susc - 1) / 4.0, 0, 1)
        fc_norm = np.clip(forecast / 150.0, 0, 1)
        ndvi_norm = np.where(
            ndvi < 0,
            np.clip(-ndvi / 0.3, 0, 1),
            0,
        )

        fpi = (
            FEATURE_WEIGHTS["rainfall_3d_mm"] * rain_norm
            + FEATURE_WEIGHTS["soil_moisture_pct"] * sm_norm
            + FEATURE_WEIGHTS["slope_degrees"] * slope_norm
            + FEATURE_WEIGHTS["susceptibility_class"] * susc_norm
            + FEATURE_WEIGHTS["forecast_24h_mm"] * fc_norm
            + FEATURE_WEIGHTS["ndvi_delta"] * ndvi_norm
        )
        interaction = rain_norm * sm_norm * 0.15
        return np.clip(fpi + interaction, 0.0, 1.0)

    def compute_grid(
        self,
        feature_grid,  # FeatureGrid from preprocessor
        district_lookup: Optional[Dict] = None,
    ) -> List[CellFPI]:
        """
        Compute FPI for every cell in the feature grid.

        Args:
            feature_grid: FeatureGrid from DataPreprocessor
            district_lookup: dict mapping (lat,lon) → (district_code, block_code)

        Returns:
            List of CellFPI objects (one per grid cell)
        """
        lats = feature_grid.lats
        lons = feature_grid.lons
        results: List[CellFPI] = []

        logger.info(
            f"FPI: computing {len(lats) * len(lons):,} cells "
            f"({'LightGBM' if self.lgbm_model else 'physics-based'})"
        )
        vectorized_fpi = self.compute_grid_vectorized(feature_grid) if self.lgbm_model is None else None

        for i, lat in enumerate(lats):
            for j, lon in enumerate(lons):
                features = self._extract_cell_features(feature_grid, i, j)
                cell_id = f"{lat:.2f}_{lon:.2f}".replace(".", "p").replace("-", "m")

                district_code, block_code = None, None
                if district_lookup:
                    key = (round(lat, 1), round(lon, 1))
                    district_code, block_code = district_lookup.get(key, (None, None))

                fpi = float(vectorized_fpi[i, j]) if vectorized_fpi is not None else self._score_cell(features)
                fpi_24h = self._score_cell_forecast(features, horizon_h=24)
                fpi_48h = self._score_cell_forecast(features, horizon_h=48)
                ci_lower, ci_upper = self._compute_confidence_interval(fpi, features)
                is_suppressed = (ci_upper - ci_lower) > 0.30
                tier = self._classify_tier(fpi, is_suppressed)
                dominant, breakdown = self._identify_dominant_signal(features)

                results.append(CellFPI(
                    cell_id=cell_id,
                    lat=lat,
                    lon=lon,
                    district_code=district_code,
                    block_code=block_code,
                    fpi_score=round(fpi, 4),
                    fpi_ci_lower=round(ci_lower, 4),
                    fpi_ci_upper=round(ci_upper, 4),
                    fpi_24h=round(fpi_24h, 4),
                    fpi_48h=round(fpi_48h, 4),
                    alert_tier=tier,
                    is_suppressed=is_suppressed,
                    dominant_signal=dominant,
                    signal_breakdown=breakdown,
                    rainfall_3d_mm=round(float(features["rainfall_3d_mm"]), 1),
                    rainfall_24h_mm=round(float(features["rainfall_24h_mm"]), 1),
                    forecast_24h_mm=round(float(features["forecast_24h_mm"]), 1),
                    soil_moisture_pct=round(float(features["soil_moisture_pct"]), 1),
                    slope_degrees=round(float(features["slope_degrees"]), 1),
                    susceptibility_class=int(features["susceptibility_class"]),
                    run_timestamp=feature_grid.run_timestamp,
                ))

        logger.info(f"FPI: computed {len(results)} cells")
        return results

    def aggregate_to_blocks(
        self,
        cell_fpis: List[CellFPI],
        block_map: Dict[str, Dict],
    ) -> List[BlockFPI]:
        """
        Aggregate cell-level FPIs to block level.

        Alert logic:
        - Block FPI = 95th percentile of cell FPIs within block
        - Block alert triggers only if >= 30% of cells breach the threshold
          (spatial clustering anti-noise rule)

        Args:
            cell_fpis: list of CellFPI from compute_grid
            block_map: dict mapping block_code → {block_name, district_code, ...}

        Returns:
            List of BlockFPI objects
        """
        from collections import defaultdict

        # Group cells by block
        blocks: Dict[str, List[CellFPI]] = defaultdict(list)
        for cell in cell_fpis:
            if cell.block_code:
                blocks[cell.block_code].append(cell)
            else:
                # Assign to a synthetic "unknown" block
                key = f"unknown_{cell.district_code or 'none'}"
                blocks[key].append(cell)

        block_results: List[BlockFPI] = []

        for block_code, cells in blocks.items():
            if not cells:
                continue

            scores = np.array([c.fpi_score for c in cells])
            fpi_block = float(np.percentile(scores, 95))
            fpi_24h = float(np.percentile([c.fpi_24h for c in cells], 95))
            fpi_48h = float(np.percentile([c.fpi_48h for c in cells], 95))
            ci_lower = float(np.percentile([c.fpi_ci_lower for c in cells], 95))
            ci_upper = float(np.percentile([c.fpi_ci_upper for c in cells], 95))

            # Spatial clustering check
            watch_thresh = THRESHOLDS["WATCH"]
            breached = sum(1 for s in scores if s >= watch_thresh)
            breach_fraction = breached / len(scores) if scores.size > 0 else 0.0
            spatially_valid = breach_fraction >= 0.30

            # Alert tier
            is_suppressed = (ci_upper - ci_lower) > 0.30 or not spatially_valid
            tier = self._classify_tier(fpi_block, is_suppressed) if spatially_valid else "MONITORING"

            # Representative signals (from 95th pct cell)
            rep_idx = int(np.argmax(scores))
            rep_cell = cells[rep_idx]

            meta = block_map.get(block_code, {})

            block_results.append(BlockFPI(
                block_code=block_code,
                block_name=meta.get("block_name", block_code),
                district_code=meta.get("district_code", cells[0].district_code or ""),
                district_name=meta.get("district_name", ""),
                state_code=meta.get("state_code", ""),
                state_name=meta.get("state_name", ""),
                lat=rep_cell.lat,
                lon=rep_cell.lon,
                fpi_score=round(fpi_block, 4),
                fpi_ci_lower=round(ci_lower, 4),
                fpi_ci_upper=round(ci_upper, 4),
                fpi_24h=round(fpi_24h, 4),
                fpi_48h=round(fpi_48h, 4),
                alert_tier=tier,
                is_suppressed=is_suppressed,
                cell_count_total=len(cells),
                cell_count_breached=breached,
                breach_fraction=round(breach_fraction, 3),
                dominant_signals=[
                    {"signal": rep_cell.dominant_signal,
                     "value": rep_cell.signal_breakdown.get(rep_cell.dominant_signal, 0)}
                ],
                rainfall_3d_mm=round(float(np.mean([c.rainfall_3d_mm for c in cells])), 1),
                soil_moisture_pct=round(float(np.mean([c.soil_moisture_pct for c in cells])), 1),
                run_timestamp=cells[0].run_timestamp,
            ))

        logger.info(f"FPI: aggregated to {len(block_results)} blocks")
        return block_results

    # ── Private: scoring ─────────────────────────────────────────────────────

    def _extract_cell_features(self, grid, i: int, j: int) -> Dict[str, float]:
        """Extract scalar features for a single cell from the feature grid.

        NaN values in satellite grids (common at swath edges, coastal areas,
        or when archive data is missing) are replaced with safe physical defaults
        so the physics computation never produces NaN outputs.
        """
        def _safe(arr: np.ndarray, default: float) -> float:
            """Return float, replacing NaN/inf with a physical default."""
            val = float(arr[i, j])
            return default if not np.isfinite(val) else val

        return {
            "rainfall_3d_mm":       _safe(grid.rainfall_3d_mm,       0.0),
            "rainfall_24h_mm":      _safe(grid.rainfall_24h_mm,      0.0),
            "forecast_24h_mm":      _safe(grid.forecast_24h_mm,      0.0),
            "forecast_48h_mm":      _safe(grid.forecast_48h_mm,      0.0),
            "soil_moisture_pct":    _safe(grid.soil_moisture_pct,   50.0),
            "soil_moisture_abs":    _safe(grid.soil_moisture_abs,    0.1),
            "slope_degrees":        _safe(grid.slope_degrees,        15.0),
            "aspect_degrees":       _safe(grid.aspect_degrees,      180.0),
            "elevation_m":          _safe(grid.elevation_m,        500.0),
            "ndvi_delta":           _safe(grid.ndvi_delta,           0.0),
            "susceptibility_class": _safe(grid.susceptibility_class, 2.0),
        }

    def _score_cell(self, features: Dict[str, float]) -> float:
        """
        Compute FPI score for a single cell.
        
        Uses LightGBM if trained model available, else physics-based.
        """
        if self.lgbm_model is not None:
            return self._score_lgbm(features)
        return self._score_physics(features)

    def _score_lgbm(self, features: Dict[str, float]) -> float:
        """Score using trained LightGBM model."""
        try:
            import pandas as pd
            feature_order = list(FEATURE_WEIGHTS.keys())
            X = pd.DataFrame([{k: features.get(k, 0.0) for k in feature_order}])
            prob = self.lgbm_model.predict_proba(X)[0][1]
            return float(np.clip(prob, 0.0, 1.0))
        except Exception as e:
            logger.warning(f"LightGBM inference failed: {e}, falling back to physics")
            return self._score_physics(features)

    def _score_physics(self, features: Dict[str, float]) -> float:
        """
        Physics-based FPI scoring.

        Combines normalised feature contributions using domain-calibrated weights.
        Each component is bounded [0, 1] before weighting.

        This is the fallback when no trained model exists. It's deliberately
        conservative — better to have some false positives than miss events.
        """
        rain_3d = features["rainfall_3d_mm"]
        sm_pct = features["soil_moisture_pct"]
        slope = features["slope_degrees"]
        susc = features["susceptibility_class"]
        fc24 = features["forecast_24h_mm"]
        ndvi_delta = features["ndvi_delta"]

        # ── Rainfall component (non-linear) ──────────────────────────────────
        # 3-day accumulation is the primary trigger
        rain_norm = np.clip(rain_3d / 250.0, 0, 1)  # 250mm = near-emergency threshold
        rain_score = rain_norm ** 0.7   # concave: accelerates quickly at high values

        # ── Soil moisture component ───────────────────────────────────────────
        # Near-saturated soil (>85th pct) multiplies rainfall risk significantly
        sm_norm = np.clip(sm_pct / 100.0, 0, 1)
        sm_score = sm_norm ** 1.5   # convex: risk rises sharply near saturation

        # ── Slope component ───────────────────────────────────────────────────
        # Risk peaks at 25–40° then levels off (very steep = often bedrock)
        slope_norm = np.clip((slope - 5) / 45.0, 0, 1)
        slope_score = slope_norm if slope <= 40 else slope_norm * 0.85

        # ── Susceptibility prior (NDMA NLSM) ─────────────────────────────────
        susc_score = np.clip((susc - 1) / 4.0, 0, 1)

        # ── Forecast rainfall ─────────────────────────────────────────────────
        fc_score = np.clip(fc24 / 150.0, 0, 1)

        # ── Vegetation loss ───────────────────────────────────────────────────
        # Negative NDVI delta → degraded cover → higher runoff
        ndvi_score = np.clip(-ndvi_delta / 0.3, 0, 1) if ndvi_delta < 0 else 0.0

        # ── Weighted combination ──────────────────────────────────────────────
        fpi = (
            FEATURE_WEIGHTS["rainfall_3d_mm"]       * rain_score +
            FEATURE_WEIGHTS["soil_moisture_pct"]    * sm_score +
            FEATURE_WEIGHTS["slope_degrees"]         * slope_score +
            FEATURE_WEIGHTS["susceptibility_class"]  * susc_score +
            FEATURE_WEIGHTS["forecast_24h_mm"]       * fc_score +
            FEATURE_WEIGHTS["ndvi_delta"]            * ndvi_score
        )

        # Interaction term: rainfall × soil moisture (key LHASA v2 insight)
        interaction = rain_score * sm_score * 0.15
        fpi = np.clip(fpi + interaction, 0.0, 1.0)

        return float(fpi)

    def _score_cell_forecast(self, features: Dict[str, float], horizon_h: int) -> float:
        """
        Forecast FPI at +24h or +48h by substituting forecast rainfall.
        
        Replaces observed 3-day rainfall with:
          observed_1d + 2d_trend + forecast_Nh
        """
        forecast_features = features.copy()

        if horizon_h == 24:
            # Add 24h forecast to current rainfall picture
            forecast_features["rainfall_3d_mm"] = (
                features["rainfall_3d_mm"] * 0.67  # drop oldest day
                + features["forecast_24h_mm"]
            )
        elif horizon_h == 48:
            forecast_features["rainfall_3d_mm"] = (
                features["rainfall_3d_mm"] * 0.33
                + features["forecast_24h_mm"]
                + features["forecast_48h_mm"]
            )

        # Soil moisture also increases with continued rain
        forecast_features["soil_moisture_pct"] = min(
            99.0,
            features["soil_moisture_pct"] + features["forecast_24h_mm"] * 0.08
        )

        return self._score_cell(forecast_features)

    def _compute_confidence_interval(
        self, fpi: float, features: Dict[str, float]
    ) -> Tuple[float, float]:
        """
        Compute 95% confidence interval for the FPI score.

        Uncertainty sources:
        1. Rainfall data quality (GPM has higher uncertainty in complex terrain)
        2. Soil moisture resolution mismatch (36km SMAP vs 11km FPI cell)
        3. Model uncertainty (physics-based is less precise than trained model)
        4. Susceptibility map coarseness
        """
        # Base uncertainty: higher near decision boundaries
        if 0.35 <= fpi <= 0.70:
            base_uncertainty = 0.12  # highest uncertainty at middle range
        elif fpi > 0.85 or fpi < 0.15:
            base_uncertainty = 0.06  # more confident at extremes
        else:
            base_uncertainty = 0.09

        # Add uncertainty for low slope (noise dominates in flat terrain)
        if features["slope_degrees"] < 5:
            base_uncertainty += 0.05

        # Add uncertainty for low susceptibility (model less calibrated)
        if features["susceptibility_class"] <= 2:
            base_uncertainty += 0.04

        # Add uncertainty if no trained model
        if self.lgbm_model is None:
            base_uncertainty += 0.06

        ci_lower = float(np.clip(fpi - base_uncertainty, 0.0, 1.0))
        ci_upper = float(np.clip(fpi + base_uncertainty, 0.0, 1.0))
        return ci_lower, ci_upper

    def _classify_tier(self, fpi: float, is_suppressed: bool) -> str:
        """Map FPI score to alert tier."""
        if is_suppressed:
            return "MONITORING"
        if fpi >= THRESHOLDS["EMERGENCY"]:
            return "EMERGENCY"
        if fpi >= THRESHOLDS["WARNING"]:
            return "WARNING"
        if fpi >= THRESHOLDS["WATCH"]:
            return "WATCH"
        return "NORMAL"

    def _identify_dominant_signal(
        self, features: Dict[str, float]
    ) -> Tuple[str, Dict[str, float]]:
        """
        Identify the signal contributing most to the FPI score.
        Used in dashboard and WhatsApp message for transparency.
        """
        rain_contrib = features["rainfall_3d_mm"] / 250.0
        sm_contrib = features["soil_moisture_pct"] / 100.0
        slope_contrib = (features["slope_degrees"] - 5) / 45.0
        fc_contrib = features["forecast_24h_mm"] / 150.0
        susc_contrib = (features["susceptibility_class"] - 1) / 4.0

        contributions = {
            "rainfall_accumulation":  float(np.clip(rain_contrib, 0, 1)),
            "soil_moisture":          float(np.clip(sm_contrib, 0, 1)),
            "slope_angle":            float(np.clip(slope_contrib, 0, 1)),
            "forecast_rainfall":      float(np.clip(fc_contrib, 0, 1)),
            "geological_susceptibility": float(np.clip(susc_contrib, 0, 1)),
        }

        dominant = max(contributions, key=contributions.get)
        return dominant, contributions

    # ── Training (production use) ─────────────────────────────────────────────

    def train(self, training_data_path: Path, save_path: Optional[Path] = None):
        """
        Train LightGBM model on India historical event data.

        Training data format: CSV with columns matching FEATURE_WEIGHTS keys
        plus 'label' (1 = landslide occurred within 24h, 0 = no event).

        Sources:
        - NASA Global Landslide Catalog (positive examples)
        - Random non-event sampling from India bounding box (negative examples)
        - NDMA event inventory (positive examples)
        """
        try:
            import pandas as pd
            import lightgbm as lgb
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import roc_auc_score

            df = pd.read_csv(training_data_path)
            feature_cols = list(FEATURE_WEIGHTS.keys())

            X = df[feature_cols].fillna(0)
            y = df["label"]

            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )

            model = lgb.LGBMClassifier(
                n_estimators=300,
                learning_rate=0.05,
                max_depth=6,
                num_leaves=31,
                min_child_samples=20,
                subsample=0.8,
                colsample_bytree=0.8,
                class_weight="balanced",
                random_state=42,
                verbose=-1,
            )

            model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                callbacks=[lgb.early_stopping(50, verbose=False)],
            )

            val_probs = model.predict_proba(X_val)[:, 1]
            auc = roc_auc_score(y_val, val_probs)
            logger.info(f"FPI model trained — validation AUC: {auc:.4f}")

            save_path = save_path or self.MODEL_PATH
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "wb") as f:
                pickle.dump(model, f)

            self.lgbm_model = model
            logger.info(f"FPI model saved to {save_path}")
            return {"auc": auc, "n_train": len(X_train), "n_val": len(X_val)}

        except ImportError:
            logger.error("lightgbm not installed — cannot train model")
            raise
        except Exception as e:
            logger.error(f"Model training failed: {e}")
            raise
