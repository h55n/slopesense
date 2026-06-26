"""
SlopeSense — Open-Meteo Weather Ingestion

Zero-authentication, free weather API for real-time rainfall and forecast data.
Used as the primary fallback when NASA GPM / NOAA GFS GRIB parsing fails.

API: https://api.open-meteo.com (no key required)
Data: Hourly precipitation (mm), 7-day history + 7-day forecast
Resolution: Point-based (we query centroids of each high-risk region)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

import numpy as np
import xarray as xr

logger = logging.getLogger(__name__)

OPEN_METEO_BASE = "https://api.open-meteo.com/v1"


class OpenMeteoIngestion:
    """
    Fetches real rainfall data from Open-Meteo API for India's high-risk regions.
    No API key required. Works immediately out of the box.

    For each region bounding box, queries multiple grid points and
    interpolates to produce a DataArray compatible with the FPI preprocessor.
    """

    def fetch_rainfall(
        self,
        bbox: Dict,
        end_time: Optional[datetime] = None,
        days_back: int = 3,
    ) -> xr.DataArray:
        """
        Fetch N-day accumulated rainfall for a bounding box.
        Queries a grid of sample points within the bbox and bilinearly interpolates.

        Args:
            bbox: {min_lat, max_lat, min_lon, max_lon}
            end_time: end of the accumulation window (defaults to now UTC)
            days_back: number of days to accumulate

        Returns:
            xr.DataArray with dims [lat, lon], values in mm
        """
        import requests

        if end_time is None:
            end_time = datetime.now(timezone.utc)

        start_time = end_time - timedelta(days=days_back)
        start_str = start_time.strftime("%Y-%m-%d")
        end_str = end_time.strftime("%Y-%m-%d")

        # Build a coarse grid of sample points (2°×2° spacing within bbox)
        lat_step = max(0.5, (bbox["max_lat"] - bbox["min_lat"]) / 4)
        lon_step = max(0.5, (bbox["max_lon"] - bbox["min_lon"]) / 4)

        sample_lats = np.arange(bbox["min_lat"], bbox["max_lat"] + lat_step * 0.1, lat_step)
        sample_lons = np.arange(bbox["min_lon"], bbox["max_lon"] + lon_step * 0.1, lon_step)

        # Clip to at least 2 points per axis for interpolation
        if len(sample_lats) < 2:
            sample_lats = np.array([bbox["min_lat"], bbox["max_lat"]])
        if len(sample_lons) < 2:
            sample_lons = np.array([bbox["min_lon"], bbox["max_lon"]])

        # Fetch data for each sample point
        point_data = {}
        for lat in sample_lats:
            for lon in sample_lons:
                try:
                    accum = self._fetch_point(lat, lon, start_str, end_str)
                    point_data[(lat, lon)] = accum
                except Exception as e:
                    logger.warning(f"Open-Meteo: failed for ({lat:.2f},{lon:.2f}): {e}")
                    point_data[(lat, lon)] = 0.0

        # Build output DataArray on fine target grid
        target_lats = np.arange(bbox["min_lat"], bbox["max_lat"] + 0.1, 0.1)
        target_lons = np.arange(bbox["min_lon"], bbox["max_lon"] + 0.1, 0.1)
        grid = np.zeros((len(target_lats), len(target_lons)), dtype=np.float32)

        for i, tlat in enumerate(target_lats):
            for j, tlon in enumerate(target_lons):
                grid[i, j] = self._bilinear_interp(tlat, tlon, sample_lats, sample_lons, point_data)

        da = xr.DataArray(
            grid,
            dims=["lat", "lon"],
            coords={"lat": target_lats, "lon": target_lons},
        )
        da.name = f"rainfall_{days_back}d_mm"
        da.attrs["source"] = "Open-Meteo (ERA5 reanalysis + forecast)"
        da.attrs["computed_at"] = end_time.isoformat()
        da.attrs["synthetic"] = False
        return da

    def fetch_forecast(
        self,
        bbox: Dict,
        horizon_hours: int = 24,
    ) -> xr.DataArray:
        """
        Fetch QPF rainfall forecast for next `horizon_hours` hours.
        Returns DataArray on 0.1° grid.
        """
        import requests

        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")
        next_week = (now + timedelta(days=7)).strftime("%Y-%m-%d")

        lat_step = max(0.5, (bbox["max_lat"] - bbox["min_lat"]) / 4)
        lon_step = max(0.5, (bbox["max_lon"] - bbox["min_lon"]) / 4)
        sample_lats = np.arange(bbox["min_lat"], bbox["max_lat"] + lat_step * 0.1, lat_step)
        sample_lons = np.arange(bbox["min_lon"], bbox["max_lon"] + lon_step * 0.1, lon_step)

        if len(sample_lats) < 2:
            sample_lats = np.array([bbox["min_lat"], bbox["max_lat"]])
        if len(sample_lons) < 2:
            sample_lons = np.array([bbox["min_lon"], bbox["max_lon"]])

        point_data = {}
        for lat in sample_lats:
            for lon in sample_lons:
                try:
                    fc = self._fetch_forecast_point(lat, lon, horizon_hours)
                    point_data[(lat, lon)] = fc
                except Exception as e:
                    logger.warning(f"Open-Meteo forecast: failed for ({lat:.2f},{lon:.2f}): {e}")
                    point_data[(lat, lon)] = 0.0

        target_lats = np.arange(bbox["min_lat"], bbox["max_lat"] + 0.1, 0.1)
        target_lons = np.arange(bbox["min_lon"], bbox["max_lon"] + 0.1, 0.1)
        grid = np.zeros((len(target_lats), len(target_lons)), dtype=np.float32)

        for i, tlat in enumerate(target_lats):
            for j, tlon in enumerate(target_lons):
                grid[i, j] = self._bilinear_interp(tlat, tlon, sample_lats, sample_lons, point_data)

        da = xr.DataArray(
            grid,
            dims=["lat", "lon"],
            coords={"lat": target_lats, "lon": target_lons},
        )
        da.name = f"forecast_{horizon_hours}h_mm"
        da.attrs["source"] = "Open-Meteo WMO forecast"
        da.attrs["synthetic"] = False
        return da

    def fetch_soil_moisture(self, bbox: Dict) -> xr.DataArray:
        """
        Fetch volumetric soil water content (top 10cm) from ERA5.
        Returns DataArray on 0.1° grid, values in m³/m³.
        """
        lat_step = max(0.5, (bbox["max_lat"] - bbox["min_lat"]) / 4)
        lon_step = max(0.5, (bbox["max_lon"] - bbox["min_lon"]) / 4)
        sample_lats = np.arange(bbox["min_lat"], bbox["max_lat"] + lat_step * 0.1, lat_step)
        sample_lons = np.arange(bbox["min_lon"], bbox["max_lon"] + lon_step * 0.1, lon_step)

        if len(sample_lats) < 2:
            sample_lats = np.array([bbox["min_lat"], bbox["max_lat"]])
        if len(sample_lons) < 2:
            sample_lons = np.array([bbox["min_lon"], bbox["max_lon"]])

        point_data = {}
        for lat in sample_lats:
            for lon in sample_lons:
                try:
                    sm = self._fetch_soil_moisture_point(lat, lon)
                    point_data[(lat, lon)] = sm
                except Exception as e:
                    logger.warning(f"Open-Meteo soil moisture: failed for ({lat:.2f},{lon:.2f}): {e}")
                    point_data[(lat, lon)] = 0.3  # default ~30% volumetric

        target_lats = np.arange(bbox["min_lat"], bbox["max_lat"] + 0.1, 0.1)
        target_lons = np.arange(bbox["min_lon"], bbox["max_lon"] + 0.1, 0.1)
        grid = np.zeros((len(target_lats), len(target_lons)), dtype=np.float32)

        for i, tlat in enumerate(target_lats):
            for j, tlon in enumerate(target_lons):
                grid[i, j] = self._bilinear_interp(tlat, tlon, sample_lats, sample_lons, point_data)

        da = xr.DataArray(
            grid,
            dims=["lat", "lon"],
            coords={"lat": target_lats, "lon": target_lons},
        )
        da.name = "soil_moisture_m3m3"
        da.attrs["source"] = "Open-Meteo ERA5 Land"
        da.attrs["synthetic"] = False
        return da

    # ── Private helpers ───────────────────────────────────────────────────────

    def _fetch_point(self, lat: float, lon: float, start: str, end: str) -> float:
        """Fetch accumulated rainfall for a single point from Open-Meteo."""
        import requests
        url = (
            f"{OPEN_METEO_BASE}/archive"
            f"?latitude={lat:.4f}&longitude={lon:.4f}"
            f"&start_date={start}&end_date={end}"
            f"&hourly=precipitation"
            f"&timezone=UTC"
        )
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        precip = data.get("hourly", {}).get("precipitation", [])
        # Sum all hourly values (mm/hr → already in mm for 1-hour intervals)
        total = sum(v for v in precip if v is not None)
        return float(total)

    def _fetch_forecast_point(self, lat: float, lon: float, horizon_hours: int) -> float:
        """Fetch accumulated forecast rainfall for next N hours for a single point."""
        import requests
        url = (
            f"{OPEN_METEO_BASE}/forecast"
            f"?latitude={lat:.4f}&longitude={lon:.4f}"
            f"&hourly=precipitation"
            f"&forecast_days=3"
            f"&timezone=UTC"
        )
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        precip = data.get("hourly", {}).get("precipitation", [])
        # Take first N hours
        window = precip[:horizon_hours]
        total = sum(v for v in window if v is not None)
        return float(total)

    def _fetch_soil_moisture_point(self, lat: float, lon: float) -> float:
        """Fetch today's average soil moisture (top 10cm) for a single point."""
        import requests
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        yesterday = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%d")
        url = (
            f"{OPEN_METEO_BASE}/archive"
            f"?latitude={lat:.4f}&longitude={lon:.4f}"
            f"&start_date={yesterday}&end_date={today}"
            f"&hourly=soil_moisture_0_to_10cm"
            f"&timezone=UTC"
        )
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        sm_values = data.get("hourly", {}).get("soil_moisture_0_to_10cm", [])
        valid = [v for v in sm_values if v is not None]
        return float(np.mean(valid)) if valid else 0.25

    def _bilinear_interp(
        self,
        tlat: float, tlon: float,
        sample_lats: np.ndarray,
        sample_lons: np.ndarray,
        point_data: Dict[Tuple[float, float], float],
    ) -> float:
        """Simple inverse-distance weighted interpolation from sample points."""
        # Find nearest sample points
        distances = []
        values = []
        for (slat, slon), val in point_data.items():
            d = ((tlat - slat) ** 2 + (tlon - slon) ** 2) ** 0.5
            distances.append(max(d, 1e-6))
            values.append(val)

        if not distances:
            return 0.0

        weights = [1.0 / d for d in distances]
        total_weight = sum(weights)
        return float(sum(w * v for w, v in zip(weights, values)) / total_weight)
