# Changelog

All notable changes to the SlopeSense project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

**🎨 UI/UX & Frontend Ecosystem**
- **Comprehensive UI Overhaul**: Replaced baseline static styling with a premium "glassmorphism" aesthetic, utilizing sleek translucent backgrounds (`glass-panel`) and glowing lime accents (`shadow-glow-lime`).
- **Framer Motion Animations**: Integrated fluid entry, staggered layouts, and interactive hover states across all primary pages.
- **Global Theme Updates**: Updated `globals.css` with a deep-dark `editorial-shell` gradient, custom sleek webkit scrollbars, and modern typography (using Google Inter).
- **Dashboard (`/`)**: Refactored to include animated grid components, live data fetching indicators, and interactive map placeholder layouts.
- **Alert Details Page (`/alerts/[id]`)**: Added an animated layout that includes Recharts visual signal breakdowns, WhatsApp message previews (translated across 7 languages), CAP v1.2 XML rendering, and PDF report downloads.
- **State Districts Page (`/districts/[state]`)**: Implemented dynamic animated tables for viewing block-level landslide risks, complete with FPI tier sorting and visual progress bars.
- **System Status Page (`/status`)**: Built a real-time monitoring dashboard displaying API health, model run diagnostics, retrospective test results, and active data ingestion sources.
- **Registration Portal (`/register`)**: Created a polished contact registration form allowing DDMA officers, Gram Pradhans, and Aapda Mitra to subscribe to tier-specific WhatsApp alerts.
- **API Documentation (`/api-docs`)**: Integrated interactive Swagger UI documentation for all endpoints.
- **Navigation Components**: Deployed a persistent, responsive, blurred navigation header (`Navigation.tsx`).

**⚙️ Backend & API Architecture**
- **12 Fully-Featured REST Endpoints**: Developed and completed all essential endpoints via FastAPI (health, alerts, risk point-checks, retrospective datasets, historical geojson, and CAP feed).
- **FPI Engine implementation**: Implemented a comprehensive Flash flood Potential Index model combining physics-based susceptibility algorithms with a LightGBM classification slot.
- **Retrospective Validation**: Validated the model against historic landslide events (achieved 6/6 events flagged successfully at T-24h).
- **Data Ingestion pipelines**: Structured services to parse and process NASA GPM IMERG, NASA SMAP L3, Copernicus DEM, and Sentinel-2 data.
- **Alert Dispatch Services**: Integrated WhatsApp Business API webhooks (with mock validation modes) and PDF report generation endpoints.
- **Enterprise Security**: Added rate limiting (100/hr public bounds), HMAC signature verification for webhooks, CORS setups, API key authentication, and security header middlewares.
- **Test Suite Completion**: Wrote and passed 68 `pytest` cases covering data integrity, algorithmic constraints, API routes, security middleware, and integration endpoints.

### Fixed
- **API Serializations**: Resolved a `ValueError` in the retrospective summary endpoint caused by FastAPI attempting to encode `NaN` float values into standard JSON.
- **Frontend Syntax Issues**: Patched lingering mismatched `</motion.div>` tags and duplicate JSX return statements introduced during the massive UI refactoring phase.
- **Type Checking**: Rectified TypeScript (`npx tsc --noEmit`) compilation warnings in layout and alert detailing scripts.

### Removed
- **Legacy Components**: Removed old static, un-animated fallback shells from the primary Next.js pages.
