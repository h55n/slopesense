"""
SlopeSense — Data Preprocessing Pipeline

Aligns all input data sources to a common 0.1° grid.
Computes derived features: rolling accumulations, anomaly percentiles, slope class.

Pipeline steps:
1. Regrid all inputs to 0.1° lat/lon grid (FPI grid resolution)
2. Compute temporal aggregations (3-day rainfall, 3-day soil moisture mean)
3. Compute anomaly percentiles for soil moisture
4. Align timestamps and fill gaps
5. Build feature matrix for FPI model
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import xarray as xr
from scipy.interpolate import RegularGridInterpolator

logger = logging.getLogger(__name__)

# Standard FPI grid resolution
GRID_RESOLUTION_DEG = 0.1  # ~11km


@dataclass
class FeatureGrid:
    """
    Preprocessed feature set ready for FPI model inference.
    All arrays aligned to the same 0.1° grid.
    """
    # Coordinates
    lats: np.ndarray
    lons: np.ndarray
    run_timestamp: datetime

    # Rainfall features
    rainfall_3d_mm: np.ndarray         # 3-day accumulated rainfall (GPM)
    rainfall_24h_mm: np.ndarray        # last 24h rainfall
    forecast_24h_mm: np.ndarray        # GFS/IMD QPF forecast next 24h
    forecast_48h_mm: np.ndarray        # GFS/IMD QPF forecast next 48h

    # Soil moisture
    soil_moisture_pct: np.ndarray      # percentile (0–100)
    soil_moisture_abs: np.ndarray      # volumetric (m³/m³)

    # Terrain (static)
    slope_degrees: np.ndarray
    aspect_degrees: np.ndarray
    elevation_m: np.ndarray

    # Vegetation
    ndvi_delta: np.ndarray             # 10-day NDVI change

    # Static susceptibility (NDMA NLSM)
    susceptibility_class: np.ndarray   # 1 (low) – 5 (very high)

    # Data quality flags
    rainfall_synthetic: bool = False
    smap_synthetic: bool = False
    dem_synthetic: bool = False

    def to_dict(self) -> Dict:
        return {
            "lats": self.lats,
            "lons": self.lons,
            "run_timestamp": self.run_timestamp,
            "rainfall_3d_mm": self.rainfall_3d_mm,
            "rainfall_24h_mm": self.rainfall_24h_mm,
            "forecast_24h_mm": self.forecast_24h_mm,
            "forecast_48h_mm": self.forecast_48h_mm,
            "soil_moisture_pct": self.soil_moisture_pct,
            "soil_moisture_abs": self.soil_moisture_abs,
            "slope_degrees": self.slope_degrees,
            "aspect_degrees": self.aspect_degrees,
            "elevation_m": self.elevation_m,
            "ndvi_delta": self.ndvi_delta,
            "susceptibility_class": self.susceptibility_class,
        }


class DataPreprocessor:
    """
    Orchestrates ingestion and preprocessing of all data sources.
    
    Produces a FeatureGrid ready for the FPI model.
    Handles missing data gracefully with synthetic fallbacks.
    """

    def __init__(self, bbox: Optional[dict] = None):
        self.bbox = bbox or {
            "min_lat": 6.0, "max_lat": 38.0,
            "min_lon": 66.0, "max_lon": 98.0,
        }
        self.target_lats = np.arange(
            self.bbox["min_lat"],
            self.bbox["max_lat"] + GRID_RESOLUTION_DEG,
            GRID_RESOLUTION_DEG,
        )
        self.target_lons = np.arange(
            self.bbox["min_lon"],
            self.bbox["max_lon"] + GRID_RESOLUTION_DEG,
            GRID_RESOLUTION_DEG,
        )

    def build_feature_grid(self, run_time: Optional[datetime] = None) -> FeatureGrid:
        """
        Main entry point: fetch all data sources and build feature grid.
        
        Args:
            run_time: timestamp for this model run (defaults to now)
            
        Returns:
            FeatureGrid with all features aligned to 0.1° grid
        """
        if run_time is None:
            run_time = datetime.now(timezone.utc)

        logger.info(f"Building feature grid for run: {run_time.isoformat()}")

        from ..ingestion import (
            GPMIngestion, GFSIngestion, SMAPIngestion,
            DEMProcessor, Sentinel2Ingestion,
        )

        # ── 1. Rainfall (GPM / Fallback to Open-Meteo) ────────────────────────
        logger.info("Fetching GPM rainfall...")
        try:
            gpm = GPMIngestion()
            rainfall_3d = gpm.compute_accumulation(run_time, days=3, bbox=self.bbox)
            rainfall_1d = gpm.compute_accumulation(run_time, days=1, bbox=self.bbox)
            rain_synthetic = getattr(rainfall_3d.attrs, "get", lambda k, d: d)("synthetic", False)
        except Exception as e:
            logger.warning(f"GPM failed ({e}). Falling back to Open-Meteo for historical rainfall...")
            from ..ingestion.open_meteo import OpenMeteoIngestion
            om = OpenMeteoIngestion()
            # Open-Meteo provides 24h forecast, we will use it as a proxy or just synthetic if missing
            rainfall_3d = om.get_24h_forecast_mm(bbox=self.bbox) * 2.5 # proxy
            rainfall_1d = rainfall_3d / 3.0
            rain_synthetic = True

        # ── 2. Forecast (GFS) ─────────────────────────────────────────────────
        logger.info("Fetching GFS forecast...")
        gfs = GFSIngestion()
        forecast_24h = gfs.get_24h_forecast_mm(bbox=self.bbox)
        forecast_48h = gfs.get_24h_forecast_mm(bbox=self.bbox)  # in prod: use f24–f48

        # ── 3. Soil Moisture (SMAP / Fallback to Synthetic) ───────────────────
        logger.info("Fetching SMAP soil moisture...")
        try:
            smap = SMAPIngestion()
            sm_3d = smap.compute_3day_average(run_time, bbox=self.bbox)
            sm_pct = smap.compute_percentile(sm_3d, month=run_time.month)
            smap_synthetic = sm_3d.attrs.get("synthetic", False)
        except Exception as e:
            logger.warning(f"SMAP failed ({e}). Falling back to synthetic baseline...")
            # Fall back to synthetic physics baseline logic
            sm_3d = smap._generate_synthetic(run_time, self.bbox)
            sm_pct = smap.compute_percentile(sm_3d, month=run_time.month)
            smap_synthetic = True

        # ── 4. DEM (static) ───────────────────────────────────────────────────
        logger.info("Loading DEM slope grid...")
        dem_proc = DEMProcessor()
        dem_ds = dem_proc.get_slope_grid(bbox=self.bbox)
        dem_synthetic = dem_ds.attrs.get("synthetic", False)

        # ── 5. Sentinel-2 NDVI ───────────────────────────────────────────────
        logger.info("Fetching Sentinel-2 NDVI...")
        s2 = Sentinel2Ingestion()
        ndvi_delta = s2.get_ndvi_delta(self.bbox, run_time)

        # ── 6. NDMA Susceptibility Map ────────────────────────────────────────
        logger.info("Loading susceptibility map...")
        susceptibility = self._load_susceptibility_map()

        # ── 7. Regrid everything to 0.1° target grid ─────────────────────────
        logger.info("Regridding all inputs to 0.1° grid...")
        grid = FeatureGrid(
            lats=self.target_lats,
            lons=self.target_lons,
            run_timestamp=run_time,

            rainfall_3d_mm=self._regrid(rainfall_3d),
            rainfall_24h_mm=self._regrid(rainfall_1d),
            forecast_24h_mm=self._regrid(forecast_24h),
            forecast_48h_mm=self._regrid(forecast_48h),

            soil_moisture_pct=self._regrid(sm_pct),
            soil_moisture_abs=self._regrid(sm_3d),

            slope_degrees=self._regrid(dem_ds["slope_degrees"]),
            aspect_degrees=self._regrid(dem_ds["aspect_degrees"]),
            elevation_m=self._regrid(dem_ds["elevation_m"]),

            ndvi_delta=self._regrid(ndvi_delta),
            susceptibility_class=susceptibility,

            rainfall_synthetic=bool(rain_synthetic),
            smap_synthetic=bool(smap_synthetic),
            dem_synthetic=bool(dem_synthetic),
        )

        logger.info(
            f"Feature grid built: {len(self.target_lats)}×{len(self.target_lons)} cells "
            f"({len(self.target_lats) * len(self.target_lons):,} total)"
        )
        return grid

    def _regrid(self, da: xr.DataArray) -> np.ndarray:
        """
        Bilinear interpolation of arbitrary DataArray onto target 0.1° grid.
        Handles different source resolutions gracefully.
        """
        try:
            if da is None:
                return np.zeros((len(self.target_lats), len(self.target_lons)))

            # Get source coordinates
            src_lats = da.lat.values if "lat" in da.coords else da.y.values
            src_lons = da.lon.values if "lon" in da.coords else da.x.values
            src_data = da.values

            if src_data.ndim > 2:
                src_data = src_data[0]  # take first band if multi-band

            # Handle fill values
            src_data = np.where(np.isfinite(src_data), src_data, 0.0)

            # Sort coordinates (required for interpolator)
            lat_idx = np.argsort(src_lats)
            lon_idx = np.argsort(src_lons)
            src_lats = src_lats[lat_idx]
            src_lons = src_lons[lon_idx]
            src_data = src_data[np.ix_(lat_idx, lon_idx)]

            # Clip target to source range
            target_lats = np.clip(self.target_lats, src_lats[0], src_lats[-1])
            target_lons = np.clip(self.target_lons, src_lons[0], src_lons[-1])

            interp = RegularGridInterpolator(
                (src_lats, src_lons),
                src_data,
                method="linear",
                bounds_error=False,
                fill_value=0.0,
            )

            # Create meshgrid for interpolation
            lat_grid, lon_grid = np.meshgrid(target_lats, target_lons, indexing="ij")
            points = np.column_stack([lat_grid.ravel(), lon_grid.ravel()])
            result = interp(points).reshape(len(target_lats), len(target_lons))

            return result.astype(np.float32)

        except Exception as e:
            logger.warning(f"Regrid failed ({e}), returning zeros")
            return np.zeros((len(self.target_lats), len(self.target_lons)), dtype=np.float32)

    def _load_susceptibility_map(self) -> np.ndarray:
        """
        Load NDMA National Landslide Susceptibility Map.
        
        Map classifies every cell 1–5:
        1 = Very Low, 2 = Low, 3 = Moderate, 4 = High, 5 = Very High
        
        Source: NDMA NLSM (1:50,000 scale shapefile)
        License: Government of India Open Data (OGDL)
        
        For hackathon: uses parameterized map based on known high-risk zones.
        Production: loads from shapefile rasterized to 0.1° grid.
        """
        susceptibility_path = Path("data/static/susceptibility_0.1deg.nc")

        if susceptibility_path.exists():
            ds = xr.open_dataset(susceptibility_path)
            return self._regrid(ds["susceptibility_class"])

        logger.info("Susceptibility: generating from known high-risk zones")
        return self._generate_susceptibility()

    def _generate_susceptibility(self) -> np.ndarray:
        """
        Parameterized susceptibility based on NDMA-published high-risk zones.
        
        High-risk zones (class 4–5):
        - Western Ghats: Kerala (8.5°–12.5°N, 75.5°–77°E)
        - Uttarakhand: (28.7°–31.5°N, 77.6°–81°E)
        - Himachal Pradesh: (30.4°–33.2°N, 75.6°–79°E)
        - Sikkim: (27°–28.2°N, 88–89°E)
        - Northeast: Mizoram, Meghalaya (21–27°N, 91–97°E)
        - Maharashtra (Raigad-Satara belt): (17–19.5°N, 73–74.5°E)
        """
        data = np.ones((len(self.target_lats), len(self.target_lons)), dtype=np.int8)

        for i, lat in enumerate(self.target_lats):
            for j, lon in enumerate(self.target_lons):
                cls = self._classify_susceptibility(lat, lon)
                data[i, j] = cls

        return data

    def _classify_susceptibility(self, lat: float, lon: float) -> int:
        """Rule-based susceptibility classification from NDMA NLSM zones."""
        # Western Ghats (Kerala/Karnataka)
        if 8.5 <= lat <= 12.5 and 75.5 <= lon <= 77.5:
            return 5
        # Uttarakhand Himalayas
        if 28.7 <= lat <= 31.5 and 77.6 <= lon <= 81.0:
            return 5
        # Himachal Pradesh
        if 30.4 <= lat <= 33.2 and 75.6 <= lon <= 79.0:
            return 4
        # Sikkim
        if 27.0 <= lat <= 28.2 and 88.0 <= lon <= 89.5:
            return 5
        # Northeast (Mizoram, Meghalaya, Manipur)
        if 21.0 <= lat <= 27.0 and 91.0 <= lon <= 97.0:
            return 4
        # Maharashtra (Sahyadri slopes)
        if 17.0 <= lat <= 19.5 and 73.0 <= lon <= 74.5:
            return 4
        # Karnataka Ghats
        if 12.5 <= lat <= 16.0 and 74.5 <= lon <= 76.5:
            return 3
        # Jammu & Kashmir foothills
        if 32.5 <= lat <= 36.0 and 73.0 <= lon <= 80.0:
            return 3
        # Arunachal Pradesh
        if 27.0 <= lat <= 29.5 and 91.5 <= lon <= 97.5:
            return 4
        # Default (plains, low risk)
        return 1
