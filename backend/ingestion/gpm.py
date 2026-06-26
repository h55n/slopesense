"""
SlopeSense — NASA GPM IMERG Ingestion

Fetches 30-minute rainfall accumulation data from NASA GPM IMERG Early Run.
Accumulates into 3-day rolling totals per 0.1° grid cell.

Data source: https://gpm.nasa.gov/data/imerg
API: NASA Earthdata (earthaccess library)
Resolution: 0.1° × 0.1°
Latency: ~4 hours from observation
Format: HDF5 / NetCDF
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import xarray as xr

logger = logging.getLogger(__name__)

# India bounding box (padded slightly for edge effects)
INDIA_BBOX = {
    "min_lat": 6.0,
    "max_lat": 38.0,
    "min_lon": 66.0,
    "max_lon": 98.0,
}

# High-risk regions bounding boxes (for focused ingestion during hackathon)
REGIONS = {
    "wayanad": {"min_lat": 11.3, "max_lat": 11.8, "min_lon": 75.7, "max_lon": 76.3},
    "uttarakhand": {"min_lat": 28.7, "max_lat": 31.5, "min_lon": 77.6, "max_lon": 81.1},
    "sikkim": {"min_lat": 27.0, "max_lat": 28.2, "min_lon": 88.0, "max_lon": 89.0},
}


class GPMIngestion:
    """
    Handles fetching and processing of NASA GPM IMERG Early Run data.
    
    GPM IMERG provides near-real-time precipitation estimates at 0.1° × 0.1°
    resolution, 30-minute temporal resolution, with ~4 hour latency.
    
    We accumulate into:
    - 24-hour totals (for current conditions)
    - 3-day rolling totals (antecedent rainfall — key FPI signal)
    """

    PRODUCT_SHORT_NAME = "GPM_3IMERGHHE"   # Half-hourly Early run
    VERSION = "07"
    DATA_DIR = Path("data/gpm")

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        self.username = username or os.environ.get("NASA_EARTHDATA_USERNAME")
        self.password = password or os.environ.get("NASA_EARTHDATA_PASSWORD")
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)

    def authenticate(self):
        """Authenticate with NASA Earthdata. Returns earthaccess auth object."""
        try:
            import earthaccess
            auth = earthaccess.login(
                strategy="environment" if self.username else "netrc"
            )
            logger.info("NASA Earthdata authentication successful")
            return auth
        except ImportError:
            logger.warning("earthaccess not installed — using mock data")
            return None
        except Exception as e:
            logger.error(f"NASA Earthdata authentication failed: {e}")
            raise

    def fetch_halfhourly(
        self,
        date: datetime,
        bbox: Optional[dict] = None,
        save_local: bool = True
    ) -> Optional[xr.Dataset]:
        """
        Fetch all 48 half-hourly granules for a given UTC date.
        
        Args:
            date: UTC date to fetch
            bbox: bounding box dict with min/max lat/lon (defaults to full India)
            save_local: cache to disk
            
        Returns:
            xarray Dataset with precipitation variable, or None on failure
        """
        if bbox is None:
            bbox = INDIA_BBOX

        date_str = date.strftime("%Y-%m-%d")
        cache_path = self.DATA_DIR / f"gpm_imerg_{date_str}.nc"

        if save_local and cache_path.exists():
            logger.info(f"GPM: loading cached data for {date_str}")
            return xr.open_dataset(cache_path)

        try:
            import earthaccess

            results = earthaccess.search_data(
                short_name=self.PRODUCT_SHORT_NAME,
                version=self.VERSION,
                temporal=(
                    date.strftime("%Y-%m-%dT00:00:00"),
                    date.strftime("%Y-%m-%dT23:59:59"),
                ),
                bounding_box=(
                    bbox["min_lon"],
                    bbox["min_lat"],
                    bbox["max_lon"],
                    bbox["max_lat"],
                ),
            )

            if not results:
                logger.warning(f"GPM: no results found for {date_str}")
                return self._generate_synthetic(date, bbox)

            logger.info(f"GPM: found {len(results)} granules for {date_str}")

            # Download and open with earthaccess
            files = earthaccess.open(results[:48])  # cap at 48 (one day)

            datasets = []
            for f in files:
                try:
                    ds = xr.open_dataset(f, group="Grid")
                    # Subset to bbox
                    ds = ds.sel(
                        lat=slice(bbox["min_lat"], bbox["max_lat"]),
                        lon=slice(bbox["min_lon"], bbox["max_lon"]),
                    )
                    datasets.append(ds["precipitationCal"])
                except Exception as e:
                    logger.warning(f"GPM: could not parse granule: {e}")
                    continue

            if not datasets:
                return self._generate_synthetic(date, bbox)

            # Concatenate along time dimension
            combined = xr.concat(datasets, dim="time")
            ds_out = combined.to_dataset(name="precipitation_mmhr")

            if save_local:
                ds_out.to_netcdf(cache_path)
                logger.info(f"GPM: cached to {cache_path}")

            return ds_out

        except Exception as e:
            logger.error(f"GPM fetch failed for {date_str}: {e}")
            return self._generate_synthetic(date, bbox)

    def compute_accumulation(
        self,
        end_date: datetime,
        days: int = 3,
        bbox: Optional[dict] = None,
    ) -> xr.DataArray:
        """
        Compute N-day rainfall accumulation ending at end_date.
        
        This is the primary input to the FPI model:
        - 3-day accumulation = antecedent rainfall signal
        - 1-day accumulation = current trigger signal
        
        Returns:
            DataArray with shape (lat, lon), units mm
        """
        if bbox is None:
            bbox = INDIA_BBOX

        logger.info(f"GPM: computing {days}-day accumulation ending {end_date.date()}")

        accum = None
        for d in range(days):
            target_date = end_date - timedelta(days=d)
            ds = self.fetch_halfhourly(target_date, bbox)

            if ds is None:
                logger.warning(f"GPM: missing data for {target_date.date()}, using zeros")
                continue

            # Sum half-hourly (mm/hr × 0.5h = mm per interval)
            daily_mm = (ds["precipitation_mmhr"] * 0.5).sum(dim="time")

            if accum is None:
                accum = daily_mm
            else:
                accum = accum + daily_mm

        if accum is None:
            # Return zeros if all fetches failed
            logger.error("GPM: all fetches failed, returning zero accumulation")
            accum = xr.DataArray(
                np.zeros((int((bbox["max_lat"] - bbox["min_lat"]) / 0.1) + 1,
                          int((bbox["max_lon"] - bbox["min_lon"]) / 0.1) + 1)),
                dims=["lat", "lon"],
            )

        accum.name = f"rainfall_{days}d_mm"
        accum.attrs["description"] = f"{days}-day accumulated rainfall (mm)"
        accum.attrs["source"] = "NASA GPM IMERG Early Run"
        accum.attrs["computed_at"] = end_date.isoformat()

        return accum

    def _generate_synthetic(self, date: datetime, bbox: dict) -> xr.Dataset:
        """
        Generate synthetic GPM data for development/hackathon use when
        NASA credentials are unavailable. Uses realistic monsoon patterns.
        
        For Wayanad region during active monsoon: 30–80 mm/day typical,
        150–300 mm/day during extreme events.
        """
        logger.info(f"GPM: generating synthetic data for {date.date()}")

        lats = np.arange(bbox["min_lat"], bbox["max_lat"] + 0.1, 0.1)
        lons = np.arange(bbox["min_lon"], bbox["max_lon"] + 0.1, 0.1)
        times = np.array([(date + timedelta(minutes=30 * i)).replace(tzinfo=None) for i in range(48)], dtype="datetime64[ns]")

        # Synthetic: monsoon-like precipitation pattern
        # Higher in Western Ghats (lon 75.5–77.5), orographic enhancement
        np.random.seed(int(date.timestamp()) % 2**32)
        
        base = np.random.exponential(scale=2.0, size=(48, len(lats), len(lons)))
        
        # Orographic enhancement near Western Ghats
        for j, lon in enumerate(lons):
            if 75.5 <= lon <= 77.5:
                base[:, :, j] *= 3.5  # 3.5x enhancement in Ghats

        data = xr.Dataset(
            {"precipitation_mmhr": (["time", "lat", "lon"], base)},
            coords={"time": times, "lat": lats, "lon": lons},
        )
        data.attrs["synthetic"] = "true"
        return data


class GFSIngestion:
    """
    Handles fetching NOAA GFS forecast data.
    
    GFS is the Plan B rainfall forecast (Plan A = IMD QPF via MoU).
    Resolution: 0.25° × 0.25°
    Forecast horizon: 384 hours
    Updated every 6 hours (00Z, 06Z, 12Z, 18Z)
    No authentication required.
    """

    BASE_URL = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
    DATA_DIR = Path("data/gfs")

    def __init__(self):
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)

    def get_latest_run_time(self) -> datetime:
        """
        GFS runs 4 times/day: 00Z, 06Z, 12Z, 18Z.
        Returns the most recent completed run time (typically 5–6 hour lag).
        """
        now = datetime.now(timezone.utc)
        run_hour = (now.hour // 6) * 6
        run_time = now.replace(hour=run_hour, minute=0, second=0, microsecond=0)

        # Subtract 6 hours to ensure the run is actually available
        if (now - run_time).total_seconds() < 3600 * 3:
            run_time -= timedelta(hours=6)

        return run_time

    def fetch_forecast(
        self,
        bbox: Optional[dict] = None,
        forecast_hours: list = [6, 12, 18, 24, 30, 36, 42, 48],
        run_time: Optional[datetime] = None,
    ) -> Optional[xr.Dataset]:
        """
        Fetch GFS QPF (precipitation forecast) for specified forecast hours.
        
        Args:
            bbox: geographic bounding box
            forecast_hours: list of forecast lead times to fetch (hours)
            run_time: GFS run time (defaults to latest available)
            
        Returns:
            xarray Dataset with APCP (accumulated precipitation) variable
        """
        if bbox is None:
            bbox = INDIA_BBOX
        if run_time is None:
            run_time = self.get_latest_run_time()

        logger.info(f"GFS: fetching forecast from {run_time} for hours {forecast_hours}")

        import requests

        date_str = run_time.strftime("%Y%m%d")
        run_str = f"{run_time.hour:02d}"
        cache_path = self.DATA_DIR / f"gfs_{date_str}_{run_str}z.nc"

        if cache_path.exists():
            logger.info(f"GFS: loading cached forecast {cache_path}")
            return xr.open_dataset(cache_path)

        datasets = []
        for fhr in forecast_hours:
            url = (
                f"{self.BASE_URL}?"
                f"file=gfs.t{run_str}z.pgrb2.0p25.f{fhr:03d}"
                f"&var_APCP=on"
                f"&subregion=&leftlon={bbox['min_lon']}&rightlon={bbox['max_lon']}"
                f"&toplat={bbox['max_lat']}&bottomlat={bbox['min_lat']}"
                f"&dir=%2Fgfs.{date_str}%2F{run_str}%2Fatmos"
            )

            try:
                response = requests.get(url, timeout=30)
                if response.status_code == 200 and len(response.content) > 1000:
                    # Parse GRIB2 response
                    import cfgrib
                    import tempfile

                    with tempfile.NamedTemporaryFile(suffix=".grib2", delete=False) as tmp:
                        tmp.write(response.content)
                        tmp_path = tmp.name

                    try:
                        ds = cfgrib.open_dataset(tmp_path)
                        ds["time_step"] = fhr
                        datasets.append(ds)
                    finally:
                        os.unlink(tmp_path)
                else:
                    logger.warning(f"GFS: no data at f{fhr:03d}, using synthetic")
            except Exception as e:
                logger.warning(f"GFS: fetch failed for f{fhr:03d}: {e}")

        if not datasets:
            return self._generate_synthetic_forecast(bbox, forecast_hours)

        combined = xr.concat(datasets, dim="forecast_hour")
        combined.to_netcdf(cache_path)
        return combined

    def get_24h_forecast_mm(
        self,
        bbox: Optional[dict] = None,
        run_time: Optional[datetime] = None,
    ) -> xr.DataArray:
        """
        Convenience method: return 24-hour accumulated precipitation forecast (mm).
        
        Sums f06 through f24 to get 24h total.
        """
        ds = self.fetch_forecast(
            bbox=bbox,
            forecast_hours=[6, 12, 18, 24],
            run_time=run_time,
        )
        if ds is None:
            return self._zero_array(bbox or INDIA_BBOX)

        try:
            if "tp" in ds:
                forecast_24h = ds["tp"].sel(forecast_hour=24, method="nearest")
            elif "acpcp" in ds:
                forecast_24h = ds["acpcp"].sum(dim="forecast_hour")
            else:
                return self._zero_array(bbox or INDIA_BBOX)

            forecast_24h.name = "forecast_24h_mm"
            forecast_24h.attrs["description"] = "24h QPF from NOAA GFS (Plan B)"
            return forecast_24h

        except Exception as e:
            logger.error(f"GFS: could not extract 24h forecast: {e}")
            return self._zero_array(bbox or INDIA_BBOX)

    def _generate_synthetic_forecast(
        self, bbox: dict, forecast_hours: list
    ) -> xr.Dataset:
        """Synthetic GFS forecast for development use."""
        logger.info("GFS: generating synthetic forecast")
        lats = np.arange(bbox["min_lat"], bbox["max_lat"] + 0.25, 0.25)
        lons = np.arange(bbox["min_lon"], bbox["max_lon"] + 0.25, 0.25)

        np.random.seed(42)
        data = np.random.exponential(
            scale=15.0, size=(len(forecast_hours), len(lats), len(lons))
        )
        # Orographic enhancement
        for j, lon in enumerate(lons):
            if 75.5 <= lon <= 77.5:
                data[:, :, j] *= 2.5

        return xr.Dataset(
            {"tp": (["forecast_hour", "lat", "lon"], data)},
            coords={"forecast_hour": forecast_hours, "lat": lats, "lon": lons},
            attrs={"synthetic": "true"},
        )

    def _zero_array(self, bbox: dict) -> xr.DataArray:
        lats = np.arange(bbox["min_lat"], bbox["max_lat"] + 0.25, 0.25)
        lons = np.arange(bbox["min_lon"], bbox["max_lon"] + 0.25, 0.25)
        return xr.DataArray(
            np.zeros((len(lats), len(lons))),
            dims=["lat", "lon"],
            coords={"lat": lats, "lon": lons},
        )
