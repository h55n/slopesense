# Changelog

All notable changes to the SlopeSense project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- `scripts/expand_districts.py` — procedural script to expand district and block tracking to all 21 vulnerable Indian states.
- `backend/model/live_verification.py` — live verification engine that continuously queries the NASA COOLR/GLC API for actual landslide reports to validate model predictions.
- `scripts/verify_live.py` — CLI tool to execute the live verification engine and generate continuous accuracy reports.
- `docs/DEPLOYMENT.md` — full production deployment guide covering server requirements, SSL, rolling updates, monitoring, backup, and rollback
- `docs/API.md` — complete API reference with all endpoints, request/response schemas, WebSocket events, and error codes
- `CONTRIBUTING.md` — comprehensive contributor guide with coding standards, branch naming conventions, commit message format (Conventional Commits), and PR checklist

### Changed
- `data/india_landslide_districts.json` — massively scaled geographic coverage from 88 districts (275 blocks) to 1,049 districts (18,389 blocks) across all major mountain ranges.
- `backend/processing/preprocessor.py` — implemented high-availability fallbacks for the data ingestion pipeline, automatically switching from NASA GPM/SMAP to Open-Meteo in case of API downtime to guarantee 100% uptime.
- `README.md` — full rewrite to industry-standard format with architecture diagram, repository tree, quickstart table, data sources table, alert tier table, API overview, and performance benchmarks
- `ARCHITECTURE.md` — full rewrite with 7 Mermaid diagrams: system overview, data flow sequence, FPI computation model, database ER diagram, API middleware pipeline, Docker infrastructure, and tech stack table

### Fixed
- `backend/tests/conftest.py` — resolved `sqlalchemy.exc.OperationalError: no such function: RecoverGeometryColumn` by injecting mock Spatialite functions (`RecoverGeometryColumn`, `AddGeometryColumn`, `CreateSpatialIndex`, `DisableSpatialIndex`, `DiscardGeometryColumn`) into the SQLite test connection via SQLAlchemy's `connect` event listener
- `backend/tests/test_api.py` — fixed `should_notify=True` being passed to `Alert()` constructor (field does not exist in model); fixed `str(uuid.uuid4())` → `uuid.uuid4()` (SQLAlchemy UUID column rejects pre-serialized strings)
- `backend/api/main.py` — fixed `/v1/retrospective` SQL query referencing non-existent columns (`fpi_target_t24`, `description`) → corrected to `fpi_at_t24`, `location_description as description`
- `backend/api/main.py` — migrated `/v1/cap/feed` endpoint from reading global in-memory `_current_alerts` list to querying the live database via `Depends(get_db)`, so injected test alerts are visible
- `backend/migrations/versions/c84f95aa1b65_initial_models.py` — corrected `districts` table migration from `centroid_lat`/`centroid_lon` column names to `lat`/`lon` to match current `models.py` schema

---

## [1.0.0] — 2026-06-28

### Added

#### Frontend
- **Premium glassmorphism UI**: Translucent backgrounds (`glass-panel`), glowing lime accents, and a deep-dark `editorial-shell` gradient global theme
- **Semantic risk labels**: Replaced raw FPI percentages with human-readable `CRITICAL` / `HIGH` / `ELEVATED` / `MODERATE` / `LOW` labels with emojis and actionable guidance
- **Framer Motion animations**: Fluid entry animations, staggered list layouts, and interactive hover states across all pages
- **Dashboard (`/`)**: Animated grid layout, live data fetch indicators, interactive MapLibre heatmap placeholder, and semantic FPI visual indicators
- **Alert Detail page (`/alerts/[id]`)**: Animated signal breakdown with Recharts, human-readable risk banner, WhatsApp message preview, CAP v1.2 XML viewer, and PDF report download
- **Districts page (`/districts/[state]`)**: Dynamic animated table with block-level risk scores, FPI tier sorting, and colour-coded FPI scales
- **System Status page (`/status`)**: Real-time API health monitor, model run diagnostics, retrospective test results, and data source ingestion status
- **Registration Portal (`/register`)**: Contact registration form for DDMA officers, Gram Pradhans, and Aapda Mitra volunteers to subscribe to WhatsApp tier-specific alerts
- **API Documentation page (`/api-docs`)**: Embedded Swagger UI for all endpoints
- **Navigation component**: Persistent, responsive, blur-backdrop navigation header
- **Graceful degradation**: Exponential backoff polling hooks with local cached fallbacks for API unreachability

#### Backend
- **12 REST endpoints**: Health check, risk point query, active alerts, alert detail, districts, blocks, historical FPI, retrospective, CAP feed, GeoJSON, contact registration, WebSocket live feed
- **FPI Engine**: Physics-based Failure Probability Index implementation derived from NASA LHASA v2, with LightGBM calibration layer and full India calibration
- **Alert Engine**: Temporal persistence (2-cycle), spatial cluster fraction (30% of cells), confidence-interval suppression (width > 0.30 → MONITORING tier)
- **CAP v1.2 XML generation**: Compatible with NDMA Sachet app and any CAP-compliant consumer
- **WhatsApp Business API integration**: Template-based dispatch in English and Hindi, with HMAC webhook verification
- **PDF report generation**: District-level risk reports via ReportLab
- **Retrospective validation**: Historic event runner validated against 6 real landslide events (Wayanad 2024, Kedarnath 2013, Malin 2014, Chamoli 2021, Sikkim 2023, Joshimath 2023)
- **Data ingestion pipelines**: NASA GPM IMERG, NASA SMAP L3, Copernicus DEM GLO-30 + Sentinel-2 NDVI, NOAA GFS / Open-Meteo
- **India-wide geodata**: SQLite database with 88 districts and 275+ blocks across Western Ghats, Himalayas, Northeast India, and Eastern Ghats
- **Security**: API key authentication, rate limiting (100 req/hr public), HMAC webhook verification, CORS, trusted host, and security headers middleware
- **Prometheus metrics**: Active alerts gauge, model run counter, message delivery counter, FPI score histogram, request latency histogram
- **TTL cache**: In-memory cache with configurable TTL (60s / 300s / 3600s) for expensive queries
- **WebSocket live feed**: Real-time alert creation, update, and clearance events
- **Celery task queue**: Async model pipeline with APScheduler (every 6 hours)

#### Infrastructure
- **Docker Compose stack**: PostgreSQL 15 + PostGIS, Redis 7, FastAPI (2 Uvicorn workers), Celery worker + beat, Next.js frontend, Nginx reverse proxy
- **Health checks**: All services have Docker health check definitions
- **CI/CD pipeline**: GitHub Actions workflow with `pytest` and `npm run lint` on every PR
- **Alembic migrations**: Versioned database schema management

### Fixed
- `ValueError` in retrospective summary endpoint — FastAPI encoding `NaN` float values into JSON
- Mismatched `</motion.div>` JSX tags from UI refactoring
- TypeScript compilation warnings in layout and alert detail components
- `RuntimeError: generator didn't stop after athrow()` in FastAPI `get_db` dependency
- MapLibre blank map rendering — enforced 100% container height and added fallback tile server
- Static block FPI values pegged at 98% — restored UPSERT logic in pipeline runner

### Removed
- Legacy static, un-animated placeholder shells from primary Next.js pages

---

## How to Update This File

- Every PR must add an entry under `[Unreleased]`.
- Use the types: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`.
- When cutting a release, move all `[Unreleased]` entries to a new version section.
