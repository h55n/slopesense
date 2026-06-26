# SlopeSense API Reference

Base URL: `https://api.slopesense.in` (production) / `http://localhost:8000` (dev)

Interactive docs: `GET /docs` (Swagger UI) | `GET /redoc` (ReDoc)

---

## Authentication

**Public endpoints** — no authentication required:
- `GET /v1/risk`
- `GET /v1/alerts/active`
- `GET /v1/geojson/fpi`
- `GET /v1/retrospective`
- `GET /v1/cap/feed`

**Authenticated endpoints** (API key in `X-API-Key` header):
- `POST /v1/contacts/register`
- `GET /v1/districts/{state}/summary`

---

## Endpoints

### Health

```
GET /
```

Response:
```json
{
  "status": "ok",
  "version": "0.1.0",
  "last_model_run": "2026-07-30T06:00:00Z",
  "active_alerts": 3
}
```

---

### Risk Score for a Point

```
GET /v1/risk?lat={lat}&lon={lon}&hours_ahead={0|24|48}
```

Returns FPI for the nearest 1km² grid cell.

**Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `lat` | float | Latitude (required) |
| `lon` | float | Longitude (required) |
| `hours_ahead` | int | Forecast horizon: 0 (now), 24, or 48 |

**Example:**
```
GET /v1/risk?lat=11.583&lon=76.083&hours_ahead=24
```

**Response:**
```json
{
  "lat": 11.583,
  "lon": 76.083,
  "cell_id": "11p58_76p08",
  "district": "Wayanad",
  "block": "Meppadi",
  "fpi_score": 0.73,
  "fpi_ci_lower": 0.61,
  "fpi_ci_upper": 0.84,
  "fpi_24h": 0.81,
  "fpi_48h": 0.77,
  "alert_tier": "WARNING",
  "dominant_signal": "rainfall_accumulation",
  "rainfall_3d_mm": 183.0,
  "soil_moisture_pct": 91.0,
  "slope_degrees": 34.0,
  "run_timestamp": "2024-07-29T06:00:00Z",
  "model_version": "v0.1"
}
```

---

### Active Alerts

```
GET /v1/alerts/active?min_fpi={0.0}&tier={WATCH|WARNING|EMERGENCY}&state={KL}
```

**Example:**
```
GET /v1/alerts/active?min_fpi=0.65&state=KL
```

**Response:**
```json
{
  "count": 1,
  "run_timestamp": "2024-07-29T06:00:00Z",
  "alerts": [
    {
      "id": "uuid",
      "alert_code": "KL_WYD_MEP_1722232800",
      "state_name": "Kerala",
      "district_name": "Wayanad",
      "block_name": "Meppadi",
      "fpi_score": 0.73,
      "fpi_ci_lower": 0.61,
      "fpi_ci_upper": 0.84,
      "fpi_24h": 0.81,
      "tier": "WARNING",
      "is_active": true,
      "is_suppressed": false,
      "consecutive_cycles": 2,
      "dominant_signals": [{"signal": "rainfall_accumulation", "value": 0.82}],
      "rainfall_3d_mm": 183.0,
      "soil_moisture_percentile": 91.0,
      "cell_count_total": 48,
      "cell_count_breached": 22,
      "breach_fraction": 0.46,
      "issued_at": "2024-07-29T06:00:00Z"
    }
  ]
}
```

---

### State Districts Summary

```
GET /v1/districts/{state_code}?min_fpi={0.0}
```

**Example:** `GET /v1/districts/KL`

---

### Historical FPI

```
GET /v1/historical/{date}/{district_code}
```

**Example:** `GET /v1/historical/2024-07-29/KL_WYD`

---

### Retrospective Validation

```
GET /v1/retrospective              # summary of all 6 events
GET /v1/retrospective/{event_id}   # single event detail
```

Event IDs: `wayanad_2024`, `sikkim_2023`, `joshimath_2023`, `chamoli_2021`, `malin_2014`, `kedarnath_2013`

**Response (summary):**
```json
{
  "run_at": "2026-06-20T10:00:00Z",
  "model_version": "v0.1",
  "total_events": 6,
  "flagged_at_t24": 4,
  "pass_criterion": "≥4/6 flagged at T-24h with FPI≥target",
  "passed": true,
  "results": [...]
}
```

---

### CAP Feed (NDMA Sachet Integration)

```
GET /v1/cap/feed?state={KL}&min_fpi={0.65}
```

Returns CAP v1.2 XML — directly consumable by NDMA Sachet app.

**Example:** `GET /v1/cap/feed?state=KL&min_fpi=0.65`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
  <identifier>KL_WYD_MEP_TEST</identifier>
  <sender>SlopeSense-v0.1@slopesense.in</sender>
  ...
</alert>
```

---

### GeoJSON (MapLibre Dashboard)

```
GET /v1/geojson/fpi?state={KL}&min_fpi={0.0}
GET /v1/geojson/alerts?min_fpi={0.40}
```

Returns GeoJSON FeatureCollection for map rendering.

---

### Contact Registration (WhatsApp Alerts)

```
POST /v1/contacts/register
Content-Type: application/json

{
  "name": "Priya Nair",
  "role": "district_collector",
  "whatsapp_number": "+919876543210",
  "state_code": "KL",
  "district_code": "KL_WYD",
  "language": "ml",
  "min_tier": "WARNING"
}
```

**Roles:** `district_collector`, `sdma_officer`, `gram_pradhan`, `aapda_mitra`, `ndrf_officer`

**Languages:** `hi` (Hindi), `ml` (Malayalam), `kn` (Kannada), `mr` (Marathi), `bn` (Bengali), `ta` (Tamil), `en` (English)

---

### WebSocket (Live Updates)

```
WS /ws/live
```

Receives live model run updates and new alerts.

**Message types:**
```json
{"type": "init", "alerts": [...], "last_run": "..."}
{"type": "model_run_complete", "cells_computed": 32000, "active_alerts": 3}
{"type": "pong", "ts": "..."}
```

---

## Alert Tier Reference

| Tier | FPI | WhatsApp | Action |
|------|-----|----------|--------|
| NORMAL | <40% | No | — |
| WATCH | 40–65% | After 3 cycles (18h) | Alert DDMA. Monitor. |
| WARNING | 65–80% | After 2 cycles (12h) | Pre-position NDRF/SDRF. Issue advisory. |
| EMERGENCY | >80% | Immediately | Evacuation advisory. All channels. |
| MONITORING | Any | No | Suppressed — CI too wide. |

---

## Rate Limits

| Tier | Limit |
|------|-------|
| Public (unauthenticated) | 100 req/hour |
| Research / NGO (free API key) | 1,000 req/hour |
| Paid (reinsurers, commercial) | 10,000 req/hour |

---

## Errors

```json
{"detail": "Alert not found"}     // 404
{"detail": "Invalid token"}       // 403
{"detail": [{"msg": "..."}]}      // 422 validation error
```
