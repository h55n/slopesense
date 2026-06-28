# SlopeSense API Reference

Full reference for all SlopeSense REST and WebSocket endpoints. The API is also documented interactively at `/docs` (Swagger UI) and `/redoc`.

**Base URL (production):** `https://api.slopesense.io`  
**Base URL (local dev):** `http://localhost:8000`

---

## Authentication

Most endpoints are public (read-only). Protected endpoints require an API key passed in the header:

```
x-api-key: YOUR_API_KEY
```

API keys can be obtained from the SlopeSense team or generated via the `/v1/apikeys` endpoint (requires admin key).

---

## Rate Limiting

| Tier | Limit |
|------|-------|
| Public (unauthenticated) | 100 requests/hour per IP |
| Authenticated | 1000 requests/hour per API key |
| Internal (trigger endpoints) | Token-protected, no limit |

Rate limit headers are returned on every response:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1719590400
```

---

## Endpoints

### Health Check

#### `GET /`

Returns current system health, model run status, and active alert count.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production",
  "active_alerts": 3,
  "last_model_run": "2024-07-29T06:00:00Z",
  "database": "connected",
  "uptime_seconds": 86400
}
```

---

### Risk Assessment

#### `GET /v1/risk`

Returns the current FPI score for a single geographic point (lat/lon).

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `lat` | float | Yes | Latitude (0.0–40.0 for India) |
| `lon` | float | Yes | Longitude (65.0–100.0 for India) |

**Example:**
```bash
curl "http://localhost:8000/v1/risk?lat=11.583&lon=76.083"
```

**Response:**
```json
{
  "lat": 11.583,
  "lon": 76.083,
  "fpi_score": 0.73,
  "fpi_ci_lower": 0.61,
  "fpi_ci_upper": 0.84,
  "alert_tier": "WARNING",
  "risk_label": "HIGH",
  "risk_description": "Significant landslide risk. Pre-position response teams.",
  "risk_color": "#FF6B35",
  "district_code": "WYD",
  "block_code": "MEP",
  "as_of": "2024-07-29T06:00:00Z",
  "signals": {
    "rainfall_3d_mm": 183,
    "soil_moisture_percentile": 91,
    "slope_degrees": 34.2
  }
}
```

**Error Responses:**
- `422` — Invalid coordinates (out of range)
- `503` — Model data not yet available

---

### Active Alerts

#### `GET /v1/alerts/active`

Returns all currently active alerts above the minimum FPI threshold.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_fpi` | float | 0.40 | Minimum FPI score filter |
| `state` | string | None | ISO state code filter (e.g., `KL`) |
| `tier` | string | None | Alert tier filter (`WATCH`, `WARNING`, `EMERGENCY`) |

**Example:**
```bash
curl "http://localhost:8000/v1/alerts/active?state=KL&min_fpi=0.65"
```

**Response:**
```json
{
  "count": 2,
  "as_of": "2024-07-29T06:00:00Z",
  "alerts": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "alert_code": "KL-WYD-MEP-20240729T060000",
      "tier": "WARNING",
      "state_name": "Kerala",
      "district_name": "Wayanad",
      "block_name": "Meppadi",
      "fpi_score": 0.73,
      "fpi_24h": 0.81,
      "lat": 11.583,
      "lon": 76.083,
      "rainfall_3d_mm": 183,
      "soil_moisture_percentile": 91,
      "issued_at": "2024-07-29T06:00:00Z",
      "risk_label": "HIGH",
      "risk_color": "#FF6B35"
    }
  ]
}
```

---

#### `GET /v1/alerts/{alert_id}`

Returns full detail for a single alert including signal breakdown.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `alert_id` | UUID | Alert UUID |

---

### Geographic Data

#### `GET /v1/districts/{state}`

Returns all districts in a state with their current FPI scores.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `state` | string | ISO state code (e.g., `KL`, `UK`, `HP`) |

**Response:**
```json
{
  "state": "KL",
  "districts": [
    {
      "district_code": "WYD",
      "district_name": "Wayanad",
      "max_fpi": 0.73,
      "p95_fpi": 0.69,
      "alert_tier": "WARNING",
      "block_count": 8,
      "blocks_above_threshold": 3
    }
  ]
}
```

---

#### `GET /v1/blocks/{district}`

Returns all blocks in a district with current FPI scores.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `district` | string | District code (e.g., `WYD`) |

---

### Historical Data

#### `GET /v1/historical/{date}/{district}`

Returns historical FPI data for a district on a given date.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `date` | string | Date in `YYYY-MM-DD` format |
| `district` | string | District code |

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `format` | string | `json` | Response format: `json` or `geojson` |

**Example:**
```bash
curl "http://localhost:8000/v1/historical/2024-07-29/WYD?format=geojson"
```

---

### Retrospective Validation

#### `GET /v1/retrospective`

Returns validation results for all historic landslide events in the database.

**Response:**
```json
{
  "total_events": 6,
  "flagged_at_t24": 4,
  "passed": 4,
  "precision": 0.83,
  "results": [
    {
      "event_id": "550e8400-...",
      "event_name": "Wayanad 2024",
      "event_date": "2024-07-30",
      "fpi_at_t24": 0.73,
      "was_flagged_24h": true
    }
  ]
}
```

#### `GET /v1/retrospective/{event_id}`

Returns the full retrospective analysis for a single historic event.

---

### CAP Alert Feed

#### `GET /v1/cap/feed`

Returns a CAP v1.2 XML alert feed, compatible with NDMA Sachet and any CAP-compliant consumer.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_fpi` | float | 0.65 | Minimum FPI score to include |
| `state` | string | None | Filter by state code |

**Example:**
```bash
curl "http://localhost:8000/v1/cap/feed?state=KL" -H "Accept: application/xml"
```

**Response:** `application/xml` — CAP v1.2 XML document. See [`docs/sample_cap.xml`](sample_cap.xml) for an example.

---

### GeoJSON Endpoints

#### `GET /v1/geojson/fpi`

Returns current FPI scores as a GeoJSON FeatureCollection (for MapLibre GL JS heatmap rendering).

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_fpi` | float | 0.30 | Minimum FPI score to include |
| `state` | string | None | Filter by state code |

**Response:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [76.083, 11.583]
      },
      "properties": {
        "fpi": 0.73,
        "fpi_pct": 73,
        "tier": "WARNING",
        "district": "Wayanad",
        "block": "Meppadi",
        "risk_label": "HIGH",
        "risk_color": "#FF6B35"
      }
    }
  ]
}
```

#### `GET /v1/geojson/alerts`

Returns active alerts as GeoJSON points (for dashboard alert markers).

---

### Contact Registration

#### `POST /v1/contacts/register`

Register a district officer, Gram Pradhan, or Aapda Mitra volunteer for WhatsApp alerts.

**Authentication:** Requires `x-api-key` header.

**Request Body:**
```json
{
  "name": "Rajesh Kumar",
  "role": "GRAM_PRADHAN",
  "state_code": "KL",
  "district_code": "WYD",
  "block_code": "MEP",
  "whatsapp_number": "+919876543210",
  "email": "rajesh@example.com",
  "min_tier": "WARNING",
  "language": "hi"
}
```

**Roles:** `SDMA_OFFICIAL`, `DDMA_OFFICIAL`, `GRAM_PRADHAN`, `AAPDA_MITRA`, `RESEARCHER`

**Response:**
```json
{
  "id": "550e8400-...",
  "name": "Rajesh Kumar",
  "status": "registered",
  "will_receive": ["WARNING", "EMERGENCY"]
}
```

---

### WebSocket

#### `WS /ws/live`

Real-time WebSocket feed that pushes alert updates, model run completions, and FPI changes.

**Connection:**
```javascript
const ws = new WebSocket("ws://localhost:8000/ws/live");
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.type, data);
};
```

**Message Types:**

| Type | Description |
|------|-------------|
| `connected` | Initial handshake with current status |
| `alert_created` | New alert issued |
| `alert_updated` | Alert tier changed |
| `alert_cleared` | Alert resolved |
| `model_run_complete` | New FPI run completed |
| `pong` | Keepalive response |

**Example message:**
```json
{
  "type": "alert_created",
  "alert_code": "KL-WYD-MEP-20240729T060000",
  "tier": "WARNING",
  "district_name": "Wayanad",
  "fpi_score": 0.73,
  "ts": "2024-07-29T06:00:00Z"
}
```

---

## Error Codes

| HTTP Code | Description |
|-----------|-------------|
| `200` | Success |
| `400` | Bad request — malformed parameters |
| `401` | Missing or invalid API key |
| `403` | Forbidden — insufficient permissions |
| `404` | Resource not found |
| `422` | Validation error — invalid parameter values |
| `429` | Rate limit exceeded |
| `500` | Internal server error |
| `503` | Service unavailable — database or model not ready |

---

## Pagination

Endpoints that return lists support cursor-based pagination:

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | int | Maximum results to return (default: 50, max: 500) |
| `offset` | int | Number of results to skip |

---

## Versioning

The API uses URL versioning (`/v1/`). Breaking changes will be introduced in a new version (`/v2/`) with a 6-month deprecation period for the previous version.
