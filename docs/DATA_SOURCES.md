# SlopeSense — Data Sources Reference

All data sources used in SlopeSense are **free and publicly accessible**.
No proprietary data is required for a functional MVP.

---

## 1. NASA GPM IMERG Early Run

**What it is:** Near-real-time global precipitation estimates from the Global Precipitation Measurement mission.

| Property | Value |
|----------|-------|
| URL | https://gpm.nasa.gov/data/imerg |
| Access | NASA Earthdata (free registration) |
| Python library | `earthaccess` |
| Resolution | 0.1° × 0.1° (~11km) |
| Temporal resolution | 30 minutes |
| Latency | ~4 hours from observation |
| Coverage | 60°S–60°N (all of India) |
| Format | HDF5 / NetCDF4 |
| Product | GPM_3IMERGHHE v07 (Early Run) |

**Registration:** https://urs.earthdata.nasa.gov (free, instant)

**Python example:**
```python
import earthaccess

earthaccess.login(strategy="environment")
results = earthaccess.search_data(
    short_name="GPM_3IMERGHHE",
    version="07",
    temporal=("2024-07-29T00:00:00", "2024-07-29T23:59:59"),
    bounding_box=(75.7, 11.3, 76.4, 11.9),  # Wayanad
)
files = earthaccess.open(results)
```

**SlopeSense use:** 3-day cumulative rainfall accumulation (primary FPI trigger signal).

---

## 2. NASA SMAP L3 Soil Moisture

**What it is:** Daily global soil moisture from the Soil Moisture Active Passive satellite.

| Property | Value |
|----------|-------|
| URL | https://nsidc.org/data/spl3smp |
| Access | NASA Earthdata (same account as GPM) |
| Resolution | 36km × 36km (EASE-Grid) |
| Temporal resolution | Daily (AM + PM overpass) |
| Latency | 24–48 hours |
| Format | HDF5 |
| Product | SPL3SMP v008 |
| Variable | `soil_moisture` (m³/m³ volumetric water content) |

**SlopeSense use:** Antecedent soil moisture — the "priming" variable. Converted to seasonal percentile rank.
Near-saturation (>85th percentile) multiplies rainfall-triggered failure probability.

**Key insight:** SMAP is used as a *state variable*, not a real-time trigger. Its 24–48h latency
is acceptable because soil moisture changes slowly (hours to days).

---

## 3. NOAA GFS (Rainfall Forecast)

**What it is:** Global Forecast System — NOAA's primary numerical weather prediction model.

| Property | Value |
|----------|-------|
| URL | https://nomads.ncep.noaa.gov |
| Access | No authentication required |
| Resolution | 0.25° × 0.25° (~28km) |
| Forecast horizon | 384 hours (16 days) |
| Update frequency | 4× daily: 00Z, 06Z, 12Z, 18Z |
| Format | GRIB2 |
| Latency | ~3–4 hours after analysis time |

**SlopeSense use:** 24h and 48h QPF (Quantitative Precipitation Forecast) — the forward-looking component.
This is **Plan B**. Plan A is IMD QPF (requires MoU with Ministry of Earth Sciences).

**Python example (GRIB2 download):**
```python
import requests

url = (
    "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl?"
    "file=gfs.t00z.pgrb2.0p25.f024"
    "&var_APCP=on"
    "&leftlon=66&rightlon=98&toplat=38&bottomlat=6"
    "&dir=%2Fgfs.20240729%2F00%2Fatmos"
)
resp = requests.get(url)
```

---

## 4. Copernicus DEM GLO-30

**What it is:** Global 30m Digital Elevation Model from ESA Copernicus.

| Property | Value |
|----------|-------|
| URL | https://dataspace.copernicus.eu |
| Access | Free (OAuth2 registration) |
| Resolution | 30m (~0.0003°) |
| Coverage | Global |
| Format | GeoTIFF (tiled) |
| Frequency | Static (updated ~annually) |
| Derived products | Slope (°), Aspect (°), Curvature |

**Registration:** https://dataspace.copernicus.eu (free)

**SlopeSense use:** Slope angle is the 3rd strongest FPI predictor. Risk peaks at 25–40°.
Computed once and cached indefinitely.

**gdaldem slope computation:**
```bash
gdaldem slope input_dem.tif slope.tif -p  # output in degrees
gdaldem aspect input_dem.tif aspect.tif
```

---

## 5. ESA Sentinel-2 L2A

**What it is:** 10m multispectral imagery from ESA's Sentinel-2 constellation.

| Property | Value |
|----------|-------|
| URL | https://dataspace.copernicus.eu |
| Access | Free (same Copernicus account) |
| Resolution | 10m (bands B4/B8 for NDVI) |
| Revisit time | 5 days (2 satellites combined) |
| Format | GeoTIFF (COG) |
| Cloud cover | Filter to <30% cloud scenes |

**SlopeSense use:** 10-day NDVI composite to detect vegetation loss (deforestation, previous slide disturbance).
Negative NDVI delta → reduced root cohesion → higher FPI. Secondary signal (5% weight).

**NDVI formula:** `NDVI = (B8 - B4) / (B8 + B4)`

---

## 6. NDMA National Landslide Susceptibility Map (NLSM)

**What it is:** India's official landslide susceptibility map at 1:50,000 scale.

| Property | Value |
|----------|-------|
| URL | https://ndma.gov.in |
| Access | Public domain (OGDL) |
| Scale | 1:50,000 |
| Format | Shapefile / PDF |
| Classes | 1 (Very Low) – 5 (Very High) |
| Coverage | All high-risk Indian states |

**SlopeSense use:** Prior susceptibility class (geological baseline). Acts as a multiplier on dynamic signals.
High-susceptibility zones require less rainfall to breach thresholds.

**Parameterized zones used in v0.1:**
- Western Ghats (Kerala 8.5–12.5°N, 75.5–77°E): Class 5
- Uttarakhand Himalayas (28.7–31.5°N, 77.6–81°E): Class 5
- Himachal Pradesh: Class 4
- Sikkim: Class 5
- Northeast India: Class 4
- Maharashtra Sahyadri: Class 4

---

## 7. NASA Global Landslide Catalog (GLC)

**What it is:** Point dataset of global landslide events 2007–present.

| Property | Value |
|----------|-------|
| URL | https://maps.nccs.nasa.gov/arcgis/apps/MapAndAppGallery |
| Format | CSV / GeoJSON |
| Coverage | Global, 2007–present |
| Update frequency | Quarterly |
| License | Free for research |

**SlopeSense use:** Model training (positive examples) and retrospective validation.
Filtered to India subset (~850 events 2007–2024).

---

## 8. IMD QPF — Plan A (Requires MoU)

**What it is:** India Meteorological Department Quantitative Precipitation Forecast.

| Property | Value |
|----------|-------|
| Access | Requires formal MoU with Ministry of Earth Sciences |
| Resolution | District-level |
| Update frequency | Every 6 hours |
| Format | API (details under NDA) |

**Status:** Blocked pending MoU. NOAA GFS is the confirmed fallback.
MoU application to be filed after MVP launch and first SDMA partnership.

---

## Data Pipeline Summary

```
Source              Resolution    Latency    Update      Use in FPI
──────────────────────────────────────────────────────────────────────
NASA GPM IMERG      0.1°/30min    4h         Every 30min   Rainfall (35% weight)
NASA SMAP L3        36km/daily    24–48h     Daily         Soil moisture (25% weight)
NOAA GFS            0.25°         3–4h       Every 6h      Forecast rainfall (8% weight)
Copernicus DEM      30m           Static     Once          Slope/aspect (15% weight)
ESA Sentinel-2      10m           5 days     5-day         NDVI delta (5% weight)
NDMA NLSM           1:50,000      Annual     Annual        Susceptibility prior (12% weight)
```

---

## Data Quality Notes

**GPM accuracy in complex terrain:** IMERG has known underestimation biases in orographic rainfall
(Western Ghats, Himalayas). The India calibration weights partially compensate for this.
In production, merging with IMD rain gauge data via kriging would improve accuracy significantly.

**SMAP resolution mismatch:** At 36km, SMAP cannot capture the soil moisture variability within a
10–20km district. The 0.1° FPI grid interpolates SMAP spatially, which introduces uncertainty.
This is reflected in the CI width (adds ~0.04 to base uncertainty).

**Sentinel-2 cloud contamination:** During peak monsoon (July–August), cloud cover >70% in
Western Ghats and Northeast India limits NDVI retrieval. MODIS Terra/Aqua (250m, daily) would be
a better option for monsoon periods despite lower resolution.
