# SlopeSense Architecture

SlopeSense is a high-availability landslide risk intelligence platform. This document outlines the system architecture, which is built around an event-driven data ingestion pipeline, an FPI inference engine, and a real-time dispatch service.

## High-Level Architecture

The architecture consists of three core domains:

1. **Ingestion & Data Pipeline**: 
   Fetches continuous raw data from satellite arrays and numerical weather models.
   - **GPM IMERG**: Fetches 30-minute rainfall data from NASA Earthdata APIs.
   - **SMAP L3**: Fetches soil moisture anomalies.
   - **NOAA GFS**: Grabs forward-looking 24-48 hour precipitation forecasts.
   - **Sentinel-2 L2A**: Fetches 5-day NDVI vegetation indices via Copernicus Data Space.

2. **Model Engine (FPI Computation)**:
   The `backend/model/` directory implements a physics-based Failure Probability Index (FPI), derived from NASA's LHASA v2 model.
   - **Dynamic Features**: Rainfall 3D, soil moisture percentile.
   - **Static Features**: Slope/Elevation (Copernicus DEM 30m), Susceptibility priors.
   - **Output**: FPI score between `0.0` and `1.0` at a 1km² resolution.

3. **Alert Dispatch & API**:
   - The FastAPI backend continuously queries the active FPI matrices.
   - If a district block crosses a threshold (`>0.65` for Warning, `>0.80` for Emergency), an `AlertEngine` creates a structured event.
   - **CAP v1.2**: Generates a standard XML alert for inter-agency routing.
   - **WhatsApp Business**: A dispatcher pushes alerts directly to village officers.

## Data Flow

1. Cron jobs (`backend/scripts/run_pipeline.py`) trigger the pipeline every 6 hours.
2. Ingestion modules download raw NetCDF and HDF5 files to `data/`.
3. Preprocessing converts everything into unified grids aligned to India's bounds.
4. FPI Engine calculates the new risk tensor.
5. The SQLite/PostgreSQL database is upserted with `active_alerts`.
6. Next.js fetches data via standard REST polling or server components to display the dashboard map.

## Tech Stack
- **Database**: PostgreSQL with PostGIS / SQLite local
- **Backend API**: FastAPI (Python)
- **Frontend**: Next.js 14 (App Router), MapLibre GL JS, TailwindCSS
- **Infrastructure**: Docker Compose, NGINX
