# SlopeSense System Architecture

SlopeSense is a real-time landslide risk intelligence platform for India. It integrates multi-source geospatial data (NASA GPM, SMAP, Copernicus DEM), computes a physics-based Failure Probability Index (FPI), and dispatches automated CAP-compliant alerts.

## 1. High-Level Architecture

```mermaid
graph TD
    %% External Data Sources
    subgraph Data Sources
        GPM[NASA GPM<br>Rainfall] --> Ing
        SMAP[NASA SMAP<br>Soil Moisture] --> Ing
        DEM[Copernicus DEM<br>Topography] --> Ing
        GFS[NOAA GFS<br>Forecast] --> Ing
    end

    %% SlopeSense Backend Core
    subgraph SlopeSense Backend (FastAPI + Async Python)
        Ing[Data Ingestion<br>fetch_pipeline.py] --> Pre[Preprocessor<br>FeatureGrid]
        Pre --> FPI[FPI Engine<br>Physics/ML Model]
        FPI --> Alert[Alert Manager<br>Threshold Evaluator]
    end

    %% Storage
    subgraph Storage Layer
        DB[(PostgreSQL / SQLite<br>+ Geo/Async)]
        Redis[(Redis<br>Cache & Rate Limiting)]
        Alert --> DB
    end

    %% External Interfaces
    subgraph Dispatch & Frontend
        Alert --> CAP[CAP v1.2 Feed<br>NDMA Sachet]
        Alert --> WA[WhatsApp Webhook<br>Twilio]
        API[FastAPI Endpoints] --> Next[Next.js Dashboard<br>Frontend]
        DB --> API
        Redis --> API
    end
```

## 2. FPI Model & Data Flow

The core of SlopeSense is the **Failure Probability Index (FPI)**. It fuses structural parameters with dynamic weather signals.

```mermaid
sequenceDiagram
    participant Worker as Background Task
    participant Ing as Ingestion (APIs)
    participant Engine as FPI Engine
    participant DB as Database
    
    Worker->>Ing: Run pipeline every 6h
    Ing->>Ing: Download Rainfall (3d, 24h)
    Ing->>Ing: Download Soil Moisture
    Ing->>Engine: Pass raw geospatial arrays
    Engine->>Engine: Interpolate to 1km² grid
    Engine->>Engine: Apply heuristic bounds (Slope, Rainfall)
    Engine->>Engine: Calculate FPI = w1*Rain + w2*Soil + w3*Slope
    Engine->>Engine: Monte Carlo CI simulation
    Engine->>DB: Upsert Risk Points
    Engine->>Worker: Trigger Alert Manager
```

## 3. Alert Tiering System

Alerts are clustered into contiguous spatial blocks. If a block breaches safety thresholds, an active alert is created.

```mermaid
stateDiagram-v2
    [*] --> NORMAL: FPI < 40% (LOW/MODERATE)
    
    NORMAL --> WATCH: FPI >= 40%
    WATCH --> NORMAL: FPI < 40%
    
    WATCH --> WARNING: FPI >= 65%
    WARNING --> WATCH: FPI < 65%
    
    WARNING --> EMERGENCY: FPI >= 80%
    EMERGENCY --> WARNING: FPI < 80%
    
    %% Alert Lifecycles
    state WATCH {
        [*] --> ActiveWatch
        ActiveWatch --> Suppressed: Admin Override
    }
    
    state WARNING {
        [*] --> ActiveWarning
        ActiveWarning --> Dispatched: CAP/WhatsApp sent
    }
    
    state EMERGENCY {
        [*] --> ActiveEmergency
        ActiveEmergency --> Evacuation: NDRF Pre-positioning
    }
```

## 4. Database Schema

```mermaid
erDiagram
    DISTRICT {
        string code PK
        string name
        string state_code
        float centroid_lat
        float centroid_lon
        int susceptibility
        boolean is_high_risk
    }
    
    BLOCK {
        string code PK
        string name
        string district_code FK
        float lat
        float lon
    }
    
    ALERT {
        string id PK
        string alert_code
        string tier "NORMAL/WATCH/WARNING/EMERGENCY"
        float fpi_score
        float rainfall_3d_mm
        datetime issued_at
    }
    
    DISTRICT ||--o{ BLOCK : "contains"
    BLOCK ||--o{ ALERT : "generates"
```

## 5. Deployment Setup

- **Frontend**: Vercel / Next.js Serverless
- **Backend API**: Dockerized FastAPI on AWS ECS / DigitalOcean App Platform
- **Database**: Amazon RDS PostgreSQL (PostGIS enabled)
- **Background Jobs**: AWS EventBridge / Celery beat
