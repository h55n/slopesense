"""
SlopeSense — Copernicus DEM + Sentinel-2 NDVI Ingestion

DEM: Copernicus GLO-30 (30m resolution) → slope, aspect, curvature
NDVI: Sentinel-2 L2A (10m, 5-day revisit) → vegetation change indicator

Data source: https://dataspace.copernicus.eu
API: Copernicus Data Space STAC API (OAuth2)
"""

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import xarray as xr
import rioxarray

logger = logging.getLogger(__name__)

INDIA_BBOX = {"min_lat": 6.0, "max_lat": 38.0, "min_lon": 66.0, "max_lon": 98.0}


class DEMProcessor:
    """
    Downloads and processes Copernicus GLO-30 DEM.
    
    Derived products used in FPI:
    - slope_degrees: terrain steepness (key failure predictor)
    - aspect: slope orientation (affects drainage and sun exposure)
    - curvature: concave slopes accumulate water → higher risk
    
    DEM is static — processed once and cached indefinitely.
    """

    DATA_DIR = Path("data/dem")
    STAC_URL = "https://stac.dataspace.copernicus.eu/v1"
    COLLECTION = "COP-DEM-GLO-30"

    def __init__(self):
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)

    def get_slope_grid(
        self,
        bbox: Optional[dict] = None,
        target_resolution_deg: float = 0.01,  # ~1km
    ) -> xr.Dataset:
        """
        Return slope and aspect grids for the given bbox.
        
        Resamples DEM from 30m to ~1km to match FPI grid.
        Uses GDAL-based slope computation.
        
        Returns:
            Dataset with slope_degrees and aspect_degrees variables
        """
        if bbox is None:
            bbox = INDIA_BBOX

        cache_key = f"slope_{bbox['min_lat']:.1f}_{bbox['max_lat']:.1f}_{bbox['min_lon']:.1f}_{bbox['max_lon']:.1f}"
        cache_path = self.DATA_DIR / f"{cache_key}.nc"

        if cache_path.exists():
            logger.info(f"DEM: loading cached slope grid from {cache_path}")
            return xr.open_dataset(cache_path)

        # Try fetching from Copernicus
        dem = self._fetch_copernicus_dem(bbox)
        if dem is None:
            logger.warning("DEM: Copernicus fetch failed, using SRTM-like synthetic")
            dem = self._generate_synthetic_dem(bbox)

        # Compute slope and aspect
        slope, aspect = self._compute_slope_aspect(dem)

        ds = xr.Dataset({
            "slope_degrees": slope,
            "aspect_degrees": aspect,
            "elevation_m": dem,
        })

        # Resample to target resolution
        ds = ds.coarsen(lat=max(1, int(target_resolution_deg / 0.0002778)), boundary="trim").mean()
        ds = ds.coarsen(lon=max(1, int(target_resolution_deg / 0.0002778)), boundary="trim").mean()

        ds.to_netcdf(cache_path)
        logger.info(f"DEM: slope grid cached to {cache_path}")
        return ds

    def _fetch_copernicus_dem(self, bbox: dict) -> Optional[xr.DataArray]:
        """
        Fetch GLO-30 DEM tiles from Copernicus Data Space.
        Requires valid client credentials.
        """
        try:
            import requests

            client_id = os.environ.get("COPERNICUS_CLIENT_ID")
            client_secret = os.environ.get("COPERNICUS_CLIENT_SECRET")

            if not client_id or not client_secret:
                logger.warning("DEM: No Copernicus credentials — using synthetic")
                return None

            # Get token
            token_resp = requests.post(
                "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "client_credentials",
                },
                timeout=30,
            )
            token = token_resp.json().get("access_token")
            if not token:
                return None

            # Search STAC for DEM tiles
            stac_resp = requests.post(
                f"{self.STAC_URL}/search",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "collections": [self.COLLECTION],
                    "bbox": [bbox["min_lon"], bbox["min_lat"], bbox["max_lon"], bbox["max_lat"]],
                    "limit": 100,
                },
                timeout=30,
            )

            if stac_resp.status_code != 200:
                logger.warning(f"DEM STAC search failed: {stac_resp.status_code}")
                return None

            items = stac_resp.json().get("features", [])
            if not items:
                return None

            logger.info(f"DEM: found {len(items)} tiles")

            # Download and mosaic tiles
            tile_arrays = []
            for item in items[:20]:  # limit tiles
                href = item["assets"].get("data", {}).get("href")
                if not href:
                    continue
                try:
                    da = rioxarray.open_rasterio(href, masked=True)
                    tile_arrays.append(da.squeeze())
                except Exception as e:
                    logger.debug(f"DEM tile load failed: {e}")

            if not tile_arrays:
                return None

            # Mosaic
            from rioxarray.merge import merge_arrays
            mosaic = merge_arrays(tile_arrays)
            mosaic.name = "elevation_m"
            return mosaic

        except Exception as e:
            logger.error(f"DEM Copernicus fetch error: {e}")
            return None

    def _compute_slope_aspect(
        self, dem: xr.DataArray
    ) -> Tuple[xr.DataArray, xr.DataArray]:
        """
        Compute slope (degrees) and aspect from DEM using finite differences.
        
        Slope formula: arctan(√(dz/dx² + dz/dy²)) × 180/π
        """
        try:
            data = dem.values.astype(float)
            
            # Resolution in meters (approximate for India lat range)
            lat_spacing_m = 111_000 * abs(float(dem.lat[1] - dem.lat[0]))
            lon_spacing_m = 111_000 * abs(float(dem.lon[1] - dem.lon[0])) * np.cos(
                np.radians(float(dem.lat.mean()))
            )

            # Gradients
            dz_dy = np.gradient(data, lat_spacing_m, axis=0)  # N-S
            dz_dx = np.gradient(data, lon_spacing_m, axis=1)  # E-W

            slope_rad = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
            slope_deg = np.degrees(slope_rad)

            aspect_rad = np.arctan2(-dz_dx, dz_dy)
            aspect_deg = np.degrees(aspect_rad) % 360

            slope = xr.DataArray(
                slope_deg, dims=dem.dims, coords=dem.coords, name="slope_degrees"
            )
            aspect = xr.DataArray(
                aspect_deg, dims=dem.dims, coords=dem.coords, name="aspect_degrees"
            )

            return slope, aspect

        except Exception as e:
            logger.error(f"DEM slope computation failed: {e}")
            # Return zeros on failure
            zeros = xr.zeros_like(dem)
            return zeros.rename("slope_degrees"), zeros.rename("aspect_degrees")

    def _generate_synthetic_dem(self, bbox: dict, resolution: float = 0.01) -> xr.DataArray:
        """
        Synthetic DEM for development.
        Mimics Western Ghats topography: steep escarpment on west side.
        """
        logger.info("DEM: generating synthetic terrain")
        lats = np.arange(bbox["min_lat"], bbox["max_lat"] + resolution, resolution)
        lons = np.arange(bbox["min_lon"], bbox["max_lon"] + resolution, resolution)

        np.random.seed(100)
        base = np.random.uniform(50, 2500, size=(len(lats), len(lons)))

        # Western Ghats escarpment: sharp rise between lon 75–76.5
        for j, lon in enumerate(lons):
            if 75.0 <= lon <= 76.0:
                base[:, j] += 800 + np.random.uniform(-200, 200, len(lats))
            elif 76.0 < lon <= 77.0:
                base[:, j] += 1200 + np.random.uniform(-300, 300, len(lats))

        # Himalayan region: high elevations in north
        for i, lat in enumerate(lats):
            if lat > 30:
                base[i, :] += 2000 + np.random.uniform(0, 2000, len(lons))

        dem = xr.DataArray(
            base.clip(0, 5000),
            dims=["lat", "lon"],
            coords={"lat": lats, "lon": lons},
            name="elevation_m",
        )
        dem.attrs["synthetic"] = "true"
        return dem

    def classify_slope_risk(self, slope_degrees: float) -> float:
        """
        Map slope angle to FPI contribution weight.
        
        Based on NDMA and GSI landslide susceptibility research for India:
        - <15°: very low slope risk
        - 15–25°: moderate
        - 25–35°: high (most failures in India in this range)
        - 35–45°: very high
        - >45°: extreme (but less common — usually bare rock)
        """
        if slope_degrees < 15:
            return 0.05
        elif slope_degrees < 25:
            return 0.25
        elif slope_degrees < 35:
            return 0.55
        elif slope_degrees < 45:
            return 0.80
        else:
            return 0.70  # Very steep = often rocky → slightly lower risk


class Sentinel2Ingestion:
    """
    Fetches Sentinel-2 NDVI to detect vegetation cover change.
    
    Vegetation loss (clear-cutting, previous slide disturbance) reduces
    root cohesion and increases surface runoff → raises failure probability.
    
    We compute 10-day NDVI composite (2 acquisitions averaged) and
    compare to 30-day baseline to detect change.
    """

    DATA_DIR = Path("data/sentinel2")
    STAC_URL = "https://stac.dataspace.copernicus.eu/v1"

    def __init__(self):
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)

    def get_ndvi_delta(
        self,
        bbox: dict,
        end_date: datetime,
        window_days: int = 10,
        baseline_days: int = 30,
    ) -> xr.DataArray:
        """
        Compute NDVI change between current 10-day window and 30-day baseline.
        
        Negative delta (vegetation loss) → increases FPI.
        
        Returns:
            DataArray with NDVI delta values (-1 to +1)
        """
        cache_path = (
            self.DATA_DIR
            / f"ndvi_delta_{end_date.strftime('%Y%m%d')}_{bbox['min_lat']:.1f}.nc"
        )

        if cache_path.exists():
            ds = xr.open_dataset(cache_path)
            return ds["ndvi_delta"]

        current_ndvi = self._fetch_ndvi_composite(bbox, end_date, window_days)
        baseline_ndvi = self._fetch_ndvi_composite(
            bbox, end_date - timedelta(days=baseline_days), window_days
        )

        if current_ndvi is None or baseline_ndvi is None:
            logger.warning("Sentinel-2: fetch failed, using zero NDVI delta")
            return self._zero_delta(bbox)

        delta = current_ndvi - baseline_ndvi
        delta.name = "ndvi_delta"
        delta.attrs["description"] = "10-day NDVI change vs 30-day baseline"

        xr.Dataset({"ndvi_delta": delta}).to_netcdf(cache_path)
        return delta

    def _fetch_ndvi_composite(
        self,
        bbox: dict,
        end_date: datetime,
        window_days: int = 10,
    ) -> Optional[xr.DataArray]:
        """Fetch cloud-masked NDVI composite from Copernicus STAC."""
        try:
            import requests

            client_id = os.environ.get("COPERNICUS_CLIENT_ID")
            client_secret = os.environ.get("COPERNICUS_CLIENT_SECRET")

            if not client_id or not client_secret:
                return self._generate_synthetic_ndvi(bbox)

            # Get OAuth token
            token_resp = requests.post(
                "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "client_credentials",
                },
                timeout=30,
            )
            token = token_resp.json().get("access_token")
            if not token:
                return self._generate_synthetic_ndvi(bbox)

            start_date = end_date - timedelta(days=window_days)
            stac_resp = requests.post(
                f"{self.STAC_URL}/search",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "collections": ["SENTINEL-2"],
                    "bbox": [bbox["min_lon"], bbox["min_lat"], bbox["max_lon"], bbox["max_lat"]],
                    "datetime": f"{start_date.strftime('%Y-%m-%dT00:00:00Z')}/{end_date.strftime('%Y-%m-%dT23:59:59Z')}",
                    "query": {"eo:cloud_cover": {"lt": 30}},
                    "limit": 5,
                    "fields": {"include": ["assets"]},
                },
                timeout=30,
            )

            if stac_resp.status_code != 200:
                return self._generate_synthetic_ndvi(bbox)

            items = stac_resp.json().get("features", [])
            if not items:
                return self._generate_synthetic_ndvi(bbox)

            ndvi_arrays = []
            for item in items[:3]:
                try:
                    b4_href = item["assets"].get("B04", {}).get("href")  # Red
                    b8_href = item["assets"].get("B08", {}).get("href")  # NIR
                    if not b4_href or not b8_href:
                        continue

                    b4 = rioxarray.open_rasterio(b4_href, masked=True).squeeze().astype(float)
                    b8 = rioxarray.open_rasterio(b8_href, masked=True).squeeze().astype(float)

                    ndvi = (b8 - b4) / (b8 + b4 + 1e-10)
                    ndvi = ndvi.clip(-1, 1)
                    ndvi_arrays.append(ndvi)
                except Exception as e:
                    logger.debug(f"Sentinel-2 tile failed: {e}")

            if not ndvi_arrays:
                return self._generate_synthetic_ndvi(bbox)

            composite = xr.concat(ndvi_arrays, dim="scene").median(dim="scene")
            composite.name = "ndvi"
            return composite

        except Exception as e:
            logger.error(f"Sentinel-2 fetch failed: {e}")
            return self._generate_synthetic_ndvi(bbox)

    def _generate_synthetic_ndvi(self, bbox: dict, resolution: float = 0.01) -> xr.DataArray:
        """Synthetic NDVI — dense forest in Western Ghats (0.7–0.9 typical)."""
        lats = np.arange(bbox["min_lat"], bbox["max_lat"] + resolution, resolution)
        lons = np.arange(bbox["min_lon"], bbox["max_lon"] + resolution, resolution)

        np.random.seed(200)
        data = np.random.normal(0.65, 0.12, (len(lats), len(lons)))

        # Western Ghats: dense forest
        for j, lon in enumerate(lons):
            if 75.5 <= lon <= 77.5:
                data[:, j] = np.random.normal(0.78, 0.08, len(lats))

        return xr.DataArray(
            data.clip(-1, 1),
            dims=["lat", "lon"],
            coords={"lat": lats, "lon": lons},
            name="ndvi",
            attrs={"synthetic": "true"},
        )

    def _zero_delta(self, bbox: dict, resolution: float = 0.01) -> xr.DataArray:
        lats = np.arange(bbox["min_lat"], bbox["max_lat"] + resolution, resolution)
        lons = np.arange(bbox["min_lon"], bbox["max_lon"] + resolution, resolution)
        return xr.DataArray(
            np.zeros((len(lats), len(lons))),
            dims=["lat", "lon"],
            coords={"lat": lats, "lon": lons},
            name="ndvi_delta",
        )
