# SlopeSense — System Architecture

This document describes the end-to-end technical architecture of the SlopeSense platform, covering data ingestion, model computation, API serving, and alert dispatch.

---

## 1. High-Level System Overview

```mermaid
graph TD
    subgraph "External Data Sources"
        GPM["NASA GPM IMERG<br/>Rainfall 0.1deg / 30min"]
        SMAP["NASA SMAP L3<br/>Soil Moisture 36km"]
        COP["Copernicus DEM GLO-30<br/>Elevation / Slope 30m"]
        SEN2["Sentinel-2 L2A<br/>NDVI 10m / 5-day"]
        GFS["NOAA GFS<br/>Forecast Rainfall 0.25deg"]
        NLSM["NDMA NLSM<br/>Susceptibility Prior"]
    end

    subgraph "Backend — Ingestion Layer"
        GPM_I["gpm.py"]
        SMAP_I["smap.py"]
        COP_I["copernicus.py"]
        GFS_I["open_meteo.py"]
    end

    subgraph "Backend — Processing Layer"
        PRE["preprocessor.py<br/>Regridding + Normalization"]
    end

    subgraph "Backend — Model Layer"
        FPI["fpi_engine.py<br/>LHASA v2 Physics + LightGBM"]
        RETRO["retrospective.py<br/>Historic Validation"]
    end

    subgraph "Backend — Alert Layer"
        AE["alert_engine.py<br/>Threshold + CAP XML"]
        DISP["dispatcher.py<br/>WhatsApp + Email"]
    end

    subgraph "Backend — API Layer"
        API["FastAPI<br/>REST + WebSocket"]
        DB["PostgreSQL + PostGIS<br/>SQLite (dev)"]
        REDIS["Redis<br/>Celery Broker"]
    end

    subgraph "Frontend"
        NEXT["Next.js 14<br/>App Router + MapLibre GL"]
    end

    subgraph "External Consumers"
        WA["WhatsApp<br/>Village Officers"]
        CAP["NDMA Sachet<br/>CAP v1.2 Feed"]
        DASH["GIS Dashboard<br/>District Collectors"]
    end

    GPM --> GPM_I
    SMAP --> SMAP_I
    COP --> COP_I
    SEN2 --> COP_I
    GFS --> GFS_I
    NLSM --> FPI

    GPM_I --> PRE
    SMAP_I --> PRE
    COP_I --> PRE
    GFS_I --> PRE

    PRE --> FPI
    FPI --> AE
    FPI --> DB
    AE --> DISP
    AE --> DB
    DISP --> WA
    API --> CAP
    API --> DB
    REDIS --> FPI

    NEXT --> API
    API --> NEXT
    NEXT --> DASH

    style FPI fill:#1a1a2e,color:#00ff88
    style AE fill:#1a1a2e,color:#ff6b35
    style API fill:#1a1a2e,color:#4da6ff
```

---

## 2. Data Flow — Step by Step

```mermaid
sequenceDiagram
    participant CRON as Cron Scheduler
    participant ING as Ingestion Modules
    participant PRE as Preprocessor
    participant FPI as FPI Engine
    participant DB as Database
    participant AE as Alert Engine
    participant DISP as Dispatcher
    participant WA as WhatsApp API
    participant API as FastAPI
    participant FE as Next.js Frontend

    CRON->>ING: trigger every 6 hours
    ING->>ING: fetch GPM, SMAP, GFS, Sentinel-2
    ING->>PRE: raw NetCDF + HDF5 files
    PRE->>PRE: regrid to 1km India grid
    PRE->>PRE: compute slope anomalies
    PRE->>FPI: unified feature tensor
    FPI->>FPI: compute FPI per cell (0.0-1.0)
    FPI->>DB: upsert fpi_grid table
    FPI->>AE: FPI grid results
    AE->>AE: aggregate block-level FPI
    AE->>AE: check thresholds (0.40/0.65/0.80)
    AE->>DB: insert/update alerts table
    AE->>DISP: active alerts above threshold
    DISP->>WA: WhatsApp Business API call
    WA-->>DISP: message_id
    DISP->>DB: log delivery status
    API->>DB: query active alerts
    API->>FE: JSON + GeoJSON responses
    FE->>FE: render MapLibre heatmap
```

---

## 3. FPI Computation Model

The **Failure Probability Index (FPI)** is derived from NASA's LHASA v2 model, calibrated for Indian sub-continent conditions.

### Signal Weights

```mermaid
graph LR
    subgraph "Dynamic Signals (updated 6h)"
        R3["3-day Rainfall Anomaly<br/>(GPM IMERG)"]
        SM["Soil Moisture Percentile<br/>(SMAP L3)"]
        RF["24h Forecast Rainfall<br/>(NOAA GFS)"]
    end

    subgraph "Static Signals (computed once)"
        SL["Slope Angle<br/>(Copernicus DEM)"]
        NDVI["NDVI Change<br/>(Sentinel-2)"]
        SUSC["Susceptibility Prior<br/>(NDMA NLSM)"]
    end

    subgraph "FPI Engine"
        W1["Weight: 0.35 (rainfall)"]
        W2["Weight: 0.25 (soil moisture)"]
        W3["Weight: 0.20 (slope)"]
        W4["Weight: 0.10 (forecast)"]
        W5["Weight: 0.10 (susceptibility)"]
        LGB["LightGBM Calibration Layer"]
        FPI_OUT["FPI Score<br/>0.0 - 1.0"]
    end

    R3 --> W1
    SM --> W2
    SL --> W3
    RF --> W4
    SUSC --> W5
    NDVI --> LGB
    W1 --> LGB
    W2 --> LGB
    W3 --> LGB
    W4 --> LGB
    W5 --> LGB
    LGB --> FPI_OUT
```

### Alert Threshold Logic

```
FPI Score ≥ 0.80  →  EMERGENCY  (consecutive cycles: 1)
FPI Score ≥ 0.65  →  WARNING    (consecutive cycles: 2)
FPI Score ≥ 0.40  →  WATCH      (consecutive cycles: 2)
FPI Score < 0.40  →  NORMAL     (no alert)

Suppression rule: if CI_upper - CI_lower > 0.30, tier → MONITORING
Spatial rule: ≥30% of cells in a block must breach threshold
```

---

## 4. Database Schema

```mermaid
erDiagram
    ALERTS {
        UUID id PK
        String alert_code UK
        String state_code
        String district_code
        String block_code
        Float fpi_score
        Float fpi_ci_lower
        Float fpi_ci_upper
        Float fpi_24h
        String tier
        Boolean is_active
        Boolean is_suppressed
        Float lat
        Float lon
        DateTime issued_at
        DateTime expires_at
    }

    FPI_GRID {
        UUID id PK
        String cell_id UK
        Float lat
        Float lon
        String state_code
        String district_code
        String block_code
        Float fpi_score
        DateTime run_timestamp
    }

    FPI_HISTORY {
        UUID id PK
        String cell_id
        Float fpi_score
        DateTime run_timestamp
    }

    DISTRICTS {
        Integer id PK
        String state_code
        String district_code UK
        String district_name
        String block_code
        String block_name
        Float centroid_lat
        Float centroid_lon
    }

    ALERT_CONTACTS {
        UUID id PK
        String name
        String role
        String district_code
        String whatsapp_number
        String email
        String min_tier_for_whatsapp
    }

    ALERT_DELIVERIES {
        UUID id PK
        UUID alert_id FK
        UUID contact_id FK
        String channel
        String recipient
        String status
        DateTime sent_at
    }

    LANDSLIDE_EVENTS {
        UUID id PK
        String event_name
        String source
        Float lat
        Float lon
        DateTime event_date
        Float fpi_at_t24
        Boolean was_flagged_24h
    }

    ALERTS ||--o{ ALERT_DELIVERIES : "generates"
    ALERT_CONTACTS ||--o{ ALERT_DELIVERIES : "receives"
    ALERTS }|--|| DISTRICTS : "references"
```

---

## 5. API Layer Architecture

```mermaid
graph TB
    subgraph "Request Pipeline"
        REQ["HTTP Request"]
        TH["TrustedHostMiddleware"]
        RL["RateLimitMiddleware<br/>100 req/hr public"]
        AK["APIKeyMiddleware<br/>optional protected routes"]
        LOG["RequestLoggingMiddleware"]
        ROUTE["Route Handler"]
        CACHE["TTL Cache Layer<br/>60s / 300s / 3600s"]
        DBSESS["AsyncSession<br/>SQLAlchemy"]
    end

    REQ --> TH --> RL --> AK --> LOG --> ROUTE
    ROUTE --> CACHE
    ROUTE --> DBSESS

    subgraph "Response Types"
        JSON["JSON Response"]
        XML["CAP v1.2 XML"]
        GJ["GeoJSON"]
        PDF["PDF Report"]
        WS["WebSocket Stream"]
    end

    ROUTE --> JSON
    ROUTE --> XML
    ROUTE --> GJ
    ROUTE --> PDF
    ROUTE --> WS
```

---

## 6. Infrastructure / Deployment

```mermaid
graph TB
    subgraph "Docker Compose Services"
        NGINX["nginx:alpine<br/>Reverse Proxy<br/>:80 / :443"]
        FE_C["slopesense-frontend<br/>Next.js 14<br/>:3000"]
        API_C["slopesense-api<br/>FastAPI + Uvicorn<br/>:8000 (2 workers)"]
        WORK["slopesense-worker<br/>Celery Worker<br/>concurrency=2"]
        SCHED["slopesense-scheduler<br/>Celery Beat<br/>every 6h"]
        DB_C["slopesense-db<br/>PostGIS 15-3.4<br/>:5432"]
        REDIS_C["slopesense-redis<br/>Redis 7 Alpine<br/>:6379"]
    end

    subgraph "Volumes"
        PG["pgdata (persistent)"]
        DATA["./data (satellite cache)"]
        LOGS["./logs"]
    end

    NGINX --> FE_C
    NGINX --> API_C
    API_C --> DB_C
    API_C --> REDIS_C
    WORK --> DB_C
    WORK --> REDIS_C
    SCHED --> REDIS_C
    SCHED --> WORK
    DB_C --- PG
    API_C --- DATA
    WORK --- DATA
    API_C --- LOGS
```

---

## 7. Tech Stack Summary

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Backend Framework** | FastAPI | 0.111 | REST API + WebSocket |
| **Async ORM** | SQLAlchemy | 2.0 | Database access |
| **Database (prod)** | PostgreSQL + PostGIS | 15.x | Geospatial queries |
| **Database (dev/test)** | SQLite + aiosqlite | — | Local development |
| **Migrations** | Alembic | 1.13 | Schema versioning |
| **Task Queue** | Celery + Redis | 5.4 | Async model runs |
| **ML Calibration** | LightGBM | 4.3 | FPI score calibration |
| **Geospatial** | GeoAlchemy2, Shapely, rasterio | — | Spatial data handling |
| **Frontend** | Next.js 14 (App Router) | 14.x | Dashboard UI |
| **Map Rendering** | MapLibre GL JS | — | GIS visualization |
| **Styling** | Tailwind CSS | — | UI design system |
| **Containerization** | Docker + Compose | 24 | Service orchestration |
| **Reverse Proxy** | Nginx | alpine | TLS, routing, static |
| **Monitoring** | Prometheus + Grafana | — | Metrics and alerting |
| **Testing** | Pytest + pytest-asyncio | 8.2 | Backend test suite |
