# Changelog

All notable changes to the SlopeSense project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

**🎨 UI/UX & Frontend Ecosystem**
- **Comprehensive UI Overhaul**: Replaced baseline static styling with a premium "glassmorphism" aesthetic, utilizing sleek translucent backgrounds (`glass-panel`) and glowing lime accents (`shadow-glow-lime`).
- **Semantic Risk Labels**: Replaced raw FPI numbers with human-readable semantic labels (CRITICAL, HIGH, ELEVATED, MODERATE, LOW) to make risks easily understandable to laypersons. Added dedicated emojis and clear actionable steps for each tier.
- **Framer Motion Animations**: Integrated fluid entry, staggered layouts, and interactive hover states across all primary pages.
- **Global Theme Updates**: Updated `globals.css` with a deep-dark `editorial-shell` gradient, custom sleek webkit scrollbars, and modern typography (using Google Inter).
- **Dashboard (`/`)**: Refactored to include animated grid components, live data fetching indicators, interactive map placeholder layouts, and semantic FPI visual indicators.
- **Alert Details Page (`/alerts/[id]`)**: Added an animated layout that includes Recharts visual signal breakdowns, human-readable risk banners, WhatsApp message previews, CAP v1.2 XML rendering, and PDF report downloads.
- **State Districts Page (`/districts/[state]`)**: Implemented dynamic animated tables for viewing block-level landslide risks, complete with FPI tier sorting, Risk Level visualization, and FPI color scales.
- **System Status Page (`/status`)**: Built a real-time monitoring dashboard displaying API health, model run diagnostics, retrospective test results, and active data ingestion sources.
- **Registration Portal (`/register`)**: Created a polished contact registration form allowing DDMA officers, Gram Pradhans, and Aapda Mitra to subscribe to tier-specific WhatsApp alerts.
- **API Documentation (`/api-docs`)**: Integrated interactive Swagger UI documentation for all endpoints.
- **Navigation Components**: Deployed a persistent, responsive, blurred navigation header (`Navigation.tsx`).
- **Frontend Resilience**: Enabled graceful degradation on the `/districts` data table to show local cached fallbacks and Exponential Backoff polling hooks rather than infinite loading skeletons when the API is unreachable.

**⚙️ Backend & API Architecture**
- **12 Fully-Featured REST Endpoints**: Developed and completed all essential endpoints via FastAPI (health, alerts, risk point-checks, retrospective datasets, historical geojson, and CAP feed).
- **FPI Engine implementation**: Implemented a comprehensive Flash flood Potential Index model combining physics-based susceptibility algorithms with a LightGBM classification slot.
- **Retrospective Validation**: Validated the model against historic landslide events (achieved 6/6 events flagged successfully at T-24h).
- **Data Ingestion pipelines**: Structured services to parse and process NASA GPM IMERG, NASA SMAP L3, Copernicus DEM, and Sentinel-2 data.
- **India-Wide Database**: Expanded SQLite database payload with 88 districts and 275+ blocks covering the Western Ghats, Himalayas, Northeast, and Eastern Ghats for precise pixel-level tracking.
- **Alert Dispatch Services**: Integrated WhatsApp Business API webhooks (with mock validation modes) and PDF report generation endpoints.
- **Enterprise Security**: Added rate limiting (100/hr public bounds), HMAC signature verification for webhooks, CORS setups, API key authentication, and security header middlewares.
- **Test Suite Completion**: Wrote and passed 100+ `pytest` cases covering data integrity, semantic risk mapping (`test_risk_labels.py`), FPI engine validations, algorithmic constraints, API routes, security middleware, and integration endpoints.

**🏗️ DevOps & Repository Maintenance**
- **Industry Standard Organization**: Restructured repository to unify duplicate folders (`data/`, `scripts/`) into single sources of truth.
- **CI/CD Integration**: Added GitHub Actions workflow (`ci.yml`) to validate PRs via `pytest` and `npm run lint`.
- **System Architecture Docs**: Added a comprehensive `system_architecture.md` containing Mermaid diagrams explaining the FPI calculation, satellite data ingestion workflows, database schemas, and alert dispatch systems.
- **Contributor Guidelines**: Wrote `CONTRIBUTING.md` emphasizing typing standards, pull request policies, and branching formats.
- **Secure GitHub Integration**: Connected the local codebase with a private GitHub remote and securely pushed the first stable commit (`v1.0`).

### Fixed
- **API Serializations**: Resolved a `ValueError` in the retrospective summary endpoint caused by FastAPI attempting to encode `NaN` float values into standard JSON.
- **Frontend Syntax Issues**: Patched lingering mismatched `</motion.div>` tags and duplicate JSX return statements introduced during the massive UI refactoring phase.
- **Type Checking**: Rectified TypeScript (`npx tsc --noEmit`) compilation warnings in layout and alert detailing scripts.
- **Database Generators**: Fixed an asyncio `RuntimeError: generator didn't stop after athrow()` exception triggered by improper teardown of the FastAPI `get_db` SQLAlchemy dependency.
- **Map Blankness**: Fixed a critical MapLibre rendering issue by enforcing a 100% container height and adding `demotiles.maplibre.org` as a fallback map tile vector.
- **Data Pipeline Consistency**: Restored missing `UPSERT` logic within `run_pipeline.py` to ensure block-level FPI calculations are correctly written to the SQLite backend and dynamically reflected in the dashboard, resolving a bug where every block was statically pegged at 98% risk.

### Removed
- **Legacy Components**: Removed old static, un-animated fallback shells from the primary Next.js pages.
