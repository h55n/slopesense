"""SlopeSense ingestion package — satellite data fetchers."""
from .gpm import GPMIngestion, GFSIngestion
from .smap import SMAPIngestion
from .copernicus import DEMProcessor, Sentinel2Ingestion
from .open_meteo import OpenMeteoIngestion

__all__ = [
    "GPMIngestion",
    "GFSIngestion",
    "SMAPIngestion",
    "DEMProcessor",
    "Sentinel2Ingestion",
    "OpenMeteoIngestion",
]
