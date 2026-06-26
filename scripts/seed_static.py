"""
SlopeSense — Static Data Seeder

Seeds static data that is computed once and cached:
  - Copernicus DEM slope/aspect grids
  - NDMA susceptibility map (parameterized)
  - District/block reference data

Usage:
    python -m scripts.seed_static
    python -m scripts.seed_static --region wayanad  # single region only
"""

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REGIONS = {
    "wayanad": {
        "name": "Wayanad, Kerala",
        "bbox": {"min_lat": 11.3, "max_lat": 11.9, "min_lon": 75.7, "max_lon": 76.4},
    },
    "uttarakhand": {
        "name": "Uttarakhand Himalayas",
        "bbox": {"min_lat": 28.7, "max_lat": 31.5, "min_lon": 77.6, "max_lon": 81.1},
    },
    "sikkim": {
        "name": "Sikkim",
        "bbox": {"min_lat": 27.0, "max_lat": 28.2, "min_lon": 88.0, "max_lon": 89.5},
    },
    "maharashtra": {
        "name": "Maharashtra Western Ghats",
        "bbox": {"min_lat": 17.0, "max_lat": 19.5, "min_lon": 73.0, "max_lon": 74.5},
    },
    "northeast": {
        "name": "Northeast India",
        "bbox": {"min_lat": 21.0, "max_lat": 27.0, "min_lon": 91.0, "max_lon": 97.0},
    },
}

ALL_INDIA = {"min_lat": 6.0, "max_lat": 38.0, "min_lon": 66.0, "max_lon": 98.0}


def seed_dem(bbox: dict, region_name: str):
    """Pre-compute and cache slope/aspect grids from Copernicus DEM."""
    from backend.ingestion.copernicus import DEMProcessor
    logger.info(f"DEM: computing slope grid for {region_name}...")
    proc = DEMProcessor()
    ds = proc.get_slope_grid(bbox=bbox)
    logger.info(f"DEM: {region_name} — slope grid shape {ds['slope_degrees'].shape}, "
                f"max slope: {float(ds['slope_degrees'].max()):.1f}°")
    return ds


def seed_susceptibility(bbox: dict, region_name: str):
    """Generate and cache NDMA susceptibility map for region."""
    from backend.processing.preprocessor import DataPreprocessor
    import numpy as np

    logger.info(f"Susceptibility: generating map for {region_name}...")
    proc = DataPreprocessor(bbox=bbox)
    susc = proc._generate_susceptibility()
    high_risk_cells = int(np.sum(susc >= 4))
    total_cells = susc.size
    logger.info(f"Susceptibility: {region_name} — {high_risk_cells}/{total_cells} cells at class 4+")

    # Save to cache
    import xarray as xr
    out_path = Path(f"data/static/susceptibility_{region_name}.nc")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lats = proc.target_lats
    lons = proc.target_lons
    ds = xr.Dataset(
        {"susceptibility_class": (["lat", "lon"], susc)},
        coords={"lat": lats, "lon": lons},
        attrs={"source": "NDMA NLSM parameterization", "generated_at": datetime.now(timezone.utc).isoformat()},
    )
    ds.to_netcdf(out_path)
    logger.info(f"Susceptibility: saved to {out_path}")
    return susc


def seed_directories():
    """Create all required data directories."""
    dirs = [
        "data/gpm", "data/gfs", "data/smap", "data/dem",
        "data/sentinel2", "data/static", "data/model",
        "data/retrospective", "logs",
    ]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
    logger.info(f"Created {len(dirs)} data directories")


def main():
    parser = argparse.ArgumentParser(description="SlopeSense Static Data Seeder")
    parser.add_argument("--region", type=str, choices=list(REGIONS.keys()) + ["all"],
                        default="all", help="Region to seed (default: all)")
    parser.add_argument("--skip-dem", action="store_true", help="Skip DEM computation")
    parser.add_argument("--skip-susceptibility", action="store_true")
    args = parser.parse_args()

    logger.info("SlopeSense static data seeder starting...")

    # Step 1: Directories
    seed_directories()

    # Step 2: Select regions
    regions = REGIONS if args.region == "all" else {args.region: REGIONS[args.region]}

    # Step 3: DEM
    if not args.skip_dem:
        for region_id, region in regions.items():
            try:
                seed_dem(region["bbox"], region["name"])
            except Exception as e:
                logger.warning(f"DEM seed failed for {region_id}: {e} — will use synthetic on first run")

    # Step 4: Susceptibility map
    if not args.skip_susceptibility:
        for region_id, region in regions.items():
            try:
                seed_susceptibility(region["bbox"], region["name"])
            except Exception as e:
                logger.warning(f"Susceptibility seed failed for {region_id}: {e}")

    logger.info("Static data seeding complete.")
    logger.info("Next step: run 'python -m scripts.retrospective' to validate the model.")


if __name__ == "__main__":
    main()
