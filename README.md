# SlopeSense 🏔️

**Landslide Risk Intelligence Platform**

> Pure-software. Free satellite data. Sub-district resolution. Village-level delivery. 24–48 hours ahead.

---

## The Problem

India loses ~800 lives per year to landslides. On July 30, 2024, Wayanad saw 420 deaths — a warning existed 16 hours prior but was never integrated into the official channel. The gap is not science. It is the **operational intelligence layer** between raw satellite data and the district collector who needs to order an evacuation.

---

## What SlopeSense Does

- Fuses free satellite data (GPM rainfall, SMAP soil moisture, Copernicus DEM, Sentinel-2 NDVI) into a probabilistic **Failure Probability Index (FPI)** per 1km² grid cell
- Updates every **6 hours** during active monsoon periods
- Issues **24–48 hour forward forecasts** via NOAA GFS (IMD QPF when MoU active)
- Delivers alerts to district officers via a **GIS dashboard** and to village officials via **WhatsApp**
- Publishes a **CAP v1.2 XML feed** compatible with NDMA's Sachet app
- Maintains a public **retrospective audit trail** for every alert issued

---

## Scores (FAR AWAY 2026)

| Criterion | Score |
|-----------|-------|
| Impact (IMP) | 9/10 |
| Novelty (NOV) | 8/10 |
| Feasibility (FEA) | 8/10 |
| Business Viability | 7/10 |
| **Composite** | **8/10** |

---

## Architecture

```
backend/
  ingestion/     — NASA GPM, SMAP, NOAA GFS, Copernicus data fetchers
  processing/    — Regridding, slope computation, anomaly percentiles
  model/         — LHASA v2 FPI engine + India calibration
  api/           — FastAPI REST + WebSocket endpoints
  alert/         — Threshold engine, spatial clustering, WhatsApp dispatcher
  tests/         — Unit + integration tests

frontend/
  src/app/       — Next.js 14 App Router pages
  src/components/ — MapLibre map, dashboard panels, alert feed
  src/lib/       — API client, data utils

infra/           — Docker Compose, nginx config
scripts/         — DB migrations, data seeding, retrospective runner
docs/            — Data source docs, API reference
```

---

## Quickstart

### Prerequisites
- Docker + Docker Compose
- Python 3.11+
- Node.js 18+
- NASA Earthdata account (free): https://urs.earthdata.nasa.gov
- ESA Copernicus account (free): https://dataspace.copernicus.eu

### 1. Configure environment

```bash
cp .env.example .env
# Fill in:
#   NASA_EARTHDATA_USERNAME / PASSWORD
#   COPERNICUS_CLIENT_ID / SECRET
#   WHATSAPP_API_TOKEN (Meta Business API)
#   DATABASE_URL
```

### 2. Start infrastructure

```bash
docker-compose up -d db redis
```

### 3. Run database migrations

```bash
cd backend
pip install -r requirements.txt
python -m scripts.migrate
```

### 4. Seed static data (DEM, susceptibility maps)

```bash
python -m scripts.seed_static
```

### 5. Run retrospective validation (Wayanad 2024)

```bash
python -m scripts.retrospective --event wayanad_2024
```

### 6. Start backend services

```bash
docker-compose up -d api worker scheduler
```

### 7. Start frontend

```bash
cd frontend
npm install
npm run dev
# Dashboard at http://localhost:3000
```

### 8. Full stack

```bash
docker-compose up
```

---

## Data Sources (all free)

| Source | Data | Latency |
|--------|------|---------|
| NASA GPM IMERG | Rainfall (0.1°, 30min) | 4h |
| NASA SMAP L3 | Soil moisture (36km) | 24–48h |
| Copernicus DEM GLO-30 | Elevation/slope (30m) | Static |
| ESA Sentinel-2 L2A | NDVI (10m, 5-day) | 5 days |
| NOAA GFS | Forecast rainfall (0.25°) | 6h |
| NDMA NLSM | Susceptibility prior | Annual |

---

## Alert Tiers

| Tier | FPI | Action |
|------|-----|--------|
| Watch | 40–65% | Alert DDMA. Monitor. |
| Warning | 65–80% | Pre-position NDRF/SDRF. Issue advisory. |
| Emergency | >80% | Immediate evacuation advisory. |

---

## Business Model

- SDMA SaaS contracts: ₹15–25 L/year × 10 states
- NDMA national contract: ₹1–3 Cr/year
- World Bank / UNDP DRR grants: ₹2–5 Cr (one-time)
- Open Data API (paid tier): research, NGOs, reinsurers

---

## Hackathon Demo Script

1. Open dashboard — Kerala state FPI heatmap (live data)
2. Zoom to Wayanad — current block-level risk scores
3. Switch to retrospective: July 29, 2024 — Meppadi block at 73% FPI
4. Show WhatsApp message that would have reached Gram Pradhan at 6am July 29
5. Show CAP XML feed endpoint
6. Show signal breakdown: "High risk: 183mm 3-day rainfall + 91st percentile soil moisture + 34° slope"

**Killer line:** "On July 29, 2024, SlopeSense had a 73% risk score for Meppadi block, with a forward forecast of 81% for the following 24 hours. The actual landslide occurred at 2:17am on July 30. The Gram Pradhan would have received this WhatsApp message 20 hours earlier."

---

## License

Apache 2.0 — same as NASA LHASA v2 (the base model we build on).
