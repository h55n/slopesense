"""Ingestion exports loaded only when requested.

The API's lightweight point registry must not import optional geospatial workers
on serverless cold starts. Research/pipeline callers retain the existing names.
"""

from importlib import import_module

_EXPORTS = {
    "GPMIngestion": (".gpm", "GPMIngestion"),
    "GFSIngestion": (".gpm", "GFSIngestion"),
    "SMAPIngestion": (".smap", "SMAPIngestion"),
    "DEMProcessor": (".copernicus", "DEMProcessor"),
    "Sentinel2Ingestion": (".copernicus", "Sentinel2Ingestion"),
    "OpenMeteoIngestion": (".open_meteo", "OpenMeteoIngestion"),
}
__all__ = list(_EXPORTS)


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(name)
    module, symbol = _EXPORTS[name]
    value = getattr(import_module(module, __name__), symbol)
    globals()[name] = value
    return value
