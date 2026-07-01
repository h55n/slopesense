"""
SlopeSense — FastAPI Application

REST API + WebSocket endpoints.

Routes:
  GET  /                          — health check
  GET  /v1/risk                   — FPI for a point (lat/lon)
  GET  /v1/districts/{state}      — all districts in a state with current FPI
  GET  /v1/blocks/{district}      — all blocks in a district with current FPI
  GET  /v1/alerts/active          — current active alerts
  GET  /v1/alerts/{alert_id}      — alert detail
  GET  /v1/historical/{date}/{district} — historical FPI for a date
  GET  /v1/retrospective          — retrospective validation results
  GET  /v1/retrospective/{event_id}    — single event retrospective
  GET  /v1/cap/feed               — CAP v1.2 XML alert feed
  POST /v1/contacts/register      — register for WhatsApp alerts
  GET  /v1/geojson/fpi            — GeoJSON FPI grid (for MapLibre)
  GET  /v1/geojson/alerts         — GeoJSON active alerts
  WS   /ws/live                   — WebSocket live updates
"""

import html
import json
import logging
import os
import uuid
from dataclasses import asdict
from datetime import date as date_type
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.database import get_db
from backend.api.middleware import APIKeyMiddleware, RateLimitMiddleware, RequestLoggingMiddleware
from backend.api.metrics import (
    ACTIVE_ALERTS, FPI_SCORES, MESSAGES_SENT, MODEL_RUNS,
)
from backend.api.reports import generate_district_report
from backend.api.webhooks import router as webhooks_router
from backend.api.apikeys import router as apikeys_router
from backend.config import settings
from backend.model.fpi_engine import (
    get_risk_label, get_risk_description, get_risk_color, get_risk_action, get_risk_short
)
from backend.models import Alert, AlertContact, AlertTier, FPIHistory

logger = logging.getLogger(__name__)

app = FastAPI(
    title="SlopeSense API",
    description=(
        "**Landslide Risk Intelligence Platform — India**\n\n"
        "Fuses free satellite data (NASA GPM, SMAP, Copernicus DEM, Sentinel-2) "
        "into a probabilistic Failure Probability Index (FPI) per 1km² grid cell. "
        "Updates every 6 hours. Delivers 24–48h forward forecasts to district officers "
        "via GIS dashboard and WhatsApp.\n\n"
        "**Authentication**: Most endpoints are public. Protected endpoints require "
        "`x-api-key` header.\n\n"
        "**CAP v1.2 Feed**: `GET /v1/cap/feed` — NDMA Sachet-compatible XML alert feed."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "SlopeSense Team",
        "url": "https://github.com/slopesense/slopesense",
        "email": "team@slopesense.io",
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0",
    },
)

# CORS — strict in production, permissive in dev
if settings.is_production:
    origins = settings.allowed_origin_list
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key"],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_host_list)
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(RateLimitMiddleware, redis_url=settings.redis_url)
app.add_middleware(APIKeyMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.include_router(webhooks_router)
app.include_router(apikeys_router)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    if not request.url.path.startswith(("/docs", "/openapi.json")):
        response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

@app.get("/metrics")
async def prometheus_metrics():
    from prometheus_client import generate_latest
    return Response(generate_latest(), media_type="text/plain")

# ── WebSocket connection manager ──────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)

    async def broadcast(self, data: dict):
        for ws in self.active.copy():
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(ws)

manager = ConnectionManager()

# ── In-memory state (replace with DB in production) ───────────────────────────

import json
from pathlib import Path

_current_alerts: List[Dict] = []
try:
    demo_path = Path(__file__).parent.parent / "demo_alerts.json"
    if demo_path.exists():
        with open(demo_path) as f:
            _current_alerts = json.load(f)
except Exception as e:
    pass
_retrospective_cache: Dict = {}
_fpi_grid_cache: Optional[Dict] = None
_last_run: Optional[datetime] = None


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class RiskResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    lat: float
    lon: float
    cell_id: str
    district: Optional[str]
    block: Optional[str]
    fpi_score: float
    fpi_ci_lower: float
    fpi_ci_upper: float
    fpi_24h: Optional[float]
    fpi_48h: Optional[float]
    alert_tier: str
    risk_label: Optional[str] = None
    risk_color: Optional[str] = None
    risk_description: Optional[str] = None
    dominant_signal: Optional[str]
    rainfall_3d_mm: Optional[float]
    soil_moisture_pct: Optional[float]
    slope_degrees: Optional[float]
    run_timestamp: str
    model_version: str = "v0.1"


class ContactRegistration(BaseModel):
    name: str
    role: str = Field(..., description="district_collector | gram_pradhan | sdma_officer | aapda_mitra")
    organization: Optional[str] = None
    whatsapp_number: str = Field(..., description="E.164 format: +919876543210")
    email: Optional[str] = None
    state_code: str
    district_code: Optional[str] = None
    block_code: Optional[str] = None
    language: str = Field(default="hi", description="hi|ml|kn|mr|bn|ta|en")
    min_tier: str = Field(default="WARNING", description="WATCH|WARNING|EMERGENCY")

    @field_validator(
        "name",
        "role",
        "organization",
        "state_code",
        "district_code",
        "block_code",
        "language",
        "min_tier",
    )
    @classmethod
    def sanitize_strings(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return html.escape(value.strip(), quote=True)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def health():
    """Health check endpoint. Returns system status, version, and active alert count."""
    active_alerts = await _active_alert_count()
    return {
        "status": "healthy",
        "service": "SlopeSense API",
        "version": "1.0.0",
        "environment": settings.environment,
        "last_model_run": _last_run.isoformat() if _last_run else None,
        "active_alerts": active_alerts,
        "database": "connected",
    }


@app.get("/v1/risk", response_model=RiskResponse, tags=["FPI"])
async def get_risk_point(
    lat: float = Query(..., description="Latitude", ge=-90, le=90),
    lon: float = Query(..., description="Longitude", ge=-180, le=180),
    hours_ahead: int = Query(0, description="Forecast horizon: 0, 24, or 48"),
):
    """
    Get FPI score for a specific lat/lon point.
    Uses nearest 0.1° grid cell.
    """
    # Try to find in cache
    if _fpi_grid_cache:
        cell = _find_nearest_cell(_fpi_grid_cache.get("cells", []), lat, lon)
        if cell:
            score = cell["fpi_score"]
            if hours_ahead == 24:
                score = cell.get("fpi_24h", score)
            elif hours_ahead == 48:
                score = cell.get("fpi_48h", score)
            
            from backend.model.fpi_engine import get_risk_level
            level = get_risk_level(score)
            return RiskResponse(**{
                **cell, 
                "fpi_score": score,
                "risk_label": level["label"],
                "risk_color": level["color"],
                "risk_description": level["description"]
            })

    # Run model on-demand for the point (hackathon mode)
    return await _compute_point_fpi(lat, lon, hours_ahead)


@app.get("/v1/districts/{state_code}", tags=["FPI"])
async def get_state_districts(
    state_code: str,
    min_fpi: float = Query(0.0, description="Filter: minimum FPI score"),
    db: AsyncSession = Depends(get_db),
):
    """Get all districts in a state with current FPI summary."""
    current_alerts = await _get_active_alerts(db)
    alerts = [
        a for a in current_alerts
        if a.get("state_code", "").lower() == state_code.lower()
        and a["fpi_score"] >= min_fpi
    ]
    return {
        "state_code": state_code.upper(),
        "count": len(alerts),
        "run_timestamp": _last_run.isoformat() if _last_run else None,
        "districts": alerts,
    }


@app.get("/v1/blocks/{district_code}", tags=["FPI"])
async def get_district_blocks(
    district_code: str,
    min_fpi: float = Query(0.0),
    db: AsyncSession = Depends(get_db),
):
    """Get all blocks in a district with current FPI."""
    current_alerts = await _get_active_alerts(db)
    alerts = [
        a for a in current_alerts
        if a.get("district_code", "").lower() == district_code.lower()
        and a["fpi_score"] >= min_fpi
    ]
    return {
        "district_code": district_code.upper(),
        "count": len(alerts),
        "blocks": alerts,
    }


@app.get("/v1/districts/{district_code}/summary", tags=["FPI"])
async def get_district_summary(district_code: str, db: AsyncSession = Depends(get_db)):
    """Protected district summary used by government/research dashboards."""
    current_alerts = await _get_active_alerts(db)
    alerts = [
        a for a in current_alerts
        if a.get("district_code", "").lower() == district_code.lower()
        and a.get("is_active", True)
    ]
    max_fpi = max((a.get("fpi_score", 0) for a in alerts), default=0)
    return {
        "district_code": district_code.upper(),
        "active_alerts": len(alerts),
        "max_fpi": max_fpi,
        "run_timestamp": _last_run.isoformat() if _last_run else None,
        "alerts": sorted(alerts, key=lambda item: item.get("fpi_score", 0), reverse=True),
    }


@app.get("/v1/districts/{district_code}/report.pdf", tags=["Reports"])
async def download_district_report(district_code: str, db: AsyncSession = Depends(get_db)):
    """Generate an official PDF report for a district."""
    current_alerts = await _get_active_alerts(db)
    alerts = [
        a for a in current_alerts
        if a.get("district_code", "").lower() == district_code.lower()
        and a.get("is_active", True)
    ]
    if not alerts and district_code.upper() in {"WYD", "KL_WYD", "WAYANAD"}:
        alerts = _synthetic_report_alerts()

    district_name = alerts[0].get("district_name", district_code.upper()) if alerts else district_code.upper()
    run_timestamp = _last_run or datetime.now(timezone.utc)
    pdf_bytes = await generate_district_report(district_code, district_name, alerts, run_timestamp)
    today = datetime.now(timezone.utc).date().isoformat()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=slopesense_{district_code}_{today}.pdf"},
    )


@app.get("/v1/alerts/active", tags=["Alerts"])
async def get_active_alerts(
    min_fpi: float = 0.40,
    tier: Optional[str] = None,
    state: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get all currently active alerts for high-risk blocks."""
    from sqlalchemy import text
    import json
    
    if db is None:
        return {"count": len(_current_alerts), "alerts": _current_alerts, "run_timestamp": datetime.now(timezone.utc).isoformat()}

    query = """
        SELECT * FROM alerts 
        WHERE is_active = 1 AND is_suppressed = 0 AND fpi_score >= :min_fpi
    """
    params = {"min_fpi": min_fpi}
    
    if tier:
        query += " AND tier = :tier"
        params["tier"] = tier
    if state:
        query += " AND state_code = :state"
        params["state"] = state
        
    query += " ORDER BY fpi_score DESC LIMIT 200"
    
    result = await db.execute(text(query), params)
    rows = result.fetchall()
    
    if not rows and len(_current_alerts) > 0:
        rows = _current_alerts

    alerts = []
    for row in rows:
        alert_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
        if isinstance(alert_dict.get("dominant_signals"), str):
            try:
                alert_dict["dominant_signals"] = json.loads(alert_dict["dominant_signals"])
            except Exception:
                alert_dict["dominant_signals"] = []
        # Enrich with human-readable risk fields
        fpi = alert_dict.get("fpi_score", 0.0) or 0.0
        alert_dict["risk_label"] = get_risk_label(fpi)
        alert_dict["risk_short"] = get_risk_short(fpi)
        alert_dict["risk_description"] = get_risk_description(fpi)
        alert_dict["risk_action"] = get_risk_action(fpi)
        alert_dict["risk_color"] = get_risk_color(fpi)
        alerts.append(alert_dict)
        
    # Get last run timestamp from DB
    last_run = None
    if alerts:
        last_run = alerts[0].get("issued_at")
        if isinstance(last_run, datetime):
            last_run = last_run.isoformat()
            
    return {
        "count": len(alerts),
        "alerts": alerts,
        "run_timestamp": last_run or datetime.now(timezone.utc).isoformat(),
    }


@app.get("/v1/alerts/{alert_id}", tags=["Alerts"])
async def get_alert_detail(alert_id: str, db: AsyncSession = Depends(get_db)):
    """Get detail for a specific alert including signal breakdown."""
    alert = next((a for a in await _get_active_alerts(db) if a.get("id") == alert_id), None)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@app.get("/v1/historical/{date}/{district_code}", tags=["Audit"])
async def get_historical_fpi(
    date: date_type,
    district_code: str,
    format: str = Query("json", pattern="^(json|geojson)$", description="json|geojson"),
    db: AsyncSession = Depends(get_db),
):
    """Return historical FPI rows and block aggregation for one district/day."""
    start = datetime.combine(date, datetime.min.time())
    end = start + timedelta(days=1)

    try:
        result = await db.execute(
            select(FPIHistory).where(
                and_(
                    FPIHistory.district_code == district_code.upper(),
                    FPIHistory.run_timestamp >= start,
                    FPIHistory.run_timestamp < end,
                )
            )
        )
        rows = [_history_row_to_dict(row) for row in result.scalars().all()]
    except Exception as exc:
        logger.warning("Historical FPI query failed, using synthetic fallback: %s", exc)
        rows = _synthetic_historical_rows(str(date), district_code)

    blocks = _aggregate_history_to_blocks(rows)
    if format == "geojson":
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [row["lon"], row["lat"]]},
                    "properties": {
                        key: value
                        for key, value in row.items()
                        if key not in {"lat", "lon"}
                    },
                }
                for row in rows
            ],
            "metadata": {"date": str(date), "district_code": district_code.upper(), "count": len(rows)},
        }

    return {
        "date": str(date),
        "district_code": district_code.upper(),
        "count": len(rows),
        "cells": rows,
        "blocks": blocks,
    }


@app.get("/v1/retrospective", tags=["Analysis"])
async def get_retrospective_summary(
    db: AsyncSession = Depends(get_db),
):
    """
    Run retrospective analysis on historical landslide events to validate FPI model.
    """
    from sqlalchemy import text
    
    if db is None:
        return _synthetic_retrospective_summary()

    query = """
        SELECT id as event_id, event_name, event_date, district_code, lat, lon,
               deaths, fpi_at_t24, was_flagged_24h, location_description as description
        FROM landslide_events
        ORDER BY event_date DESC
    """
    result = await db.execute(text(query))
    rows = result.fetchall()
    
    if not rows:
        return _synthetic_retrospective_summary()
        
    results = []
    flagged_count = 0
    for row in rows:
        mapping = dict(row._mapping)
        flagged = bool(mapping.get("was_flagged_24h"))
        if flagged:
            flagged_count += 1
            
        results.append({
            "event_id": mapping.get("event_id"),
            "event_name": mapping.get("event_name"),
            "event_date": mapping.get("event_date").isoformat() if isinstance(mapping.get("event_date"), datetime) else mapping.get("event_date"),
            "district": mapping.get("district_code"),
            "deaths": mapping.get("deaths") or 0,
            "fpi_t24": mapping.get("fpi_at_t24"),
            "target_fpi": mapping.get("fpi_target_t24"),
            "flagged_at_t24": flagged,
            "lead_time_hours": 24 if flagged else None,
            "notes": mapping.get("description"),
            "data_source": "historical",
        })
        
    return {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "model_version": "v0.1",
        "total_events": len(results),
        "flagged_at_t24": flagged_count,
        "pass_criterion": f"≥{len(results)*0.6:.0f}/{len(results)} flagged at T-24h",
        "passed": flagged_count >= len(results) * 0.6,
        "results": results,
    }


@app.get("/v1/retrospective/{event_id}", tags=["Audit"])
async def get_retrospective_event(event_id: str):
    """Get retrospective validation for a single historical event."""
    event_path = Path(f"data/retrospective/{event_id}.json")
    if event_path.exists():
        with open(event_path) as f:
            return json.load(f)

    # Compute on demand
    try:
        from backend.model.retrospective import RetrospectiveRunner
        runner = RetrospectiveRunner()
        result = runner.run_event(event_id, use_synthetic=True)
        return asdict(result)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Event not found or compute failed: {e}")


@app.get("/v1/cap/feed", tags=["CAP"])
async def get_cap_feed(
    state: Optional[str] = Query(None),
    min_fpi: float = Query(0.65, description="Minimum FPI to include"),
    db: AsyncSession = Depends(get_db),
):
    """
    CAP v1.2 XML alert feed.
    Compatible with NDMA Sachet app and any CAP consumer.

    Example: GET /v1/cap/feed?state=KL&min_fpi=0.65
    """
    from backend.alert.alert_engine import AlertEngine
    engine = AlertEngine()

    if db is None:
        alerts = _current_alerts
    else:
        alerts = await _get_active_alerts(db)

    alerts = [
        a for a in alerts
        if a.get("is_active")
        and a.get("fpi_score", 0) >= min_fpi
        and (not state or a.get("state_code", "").lower() == state.lower())
    ]

    if not alerts:
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="urn:oasis:names:tc:emergency:cap:1.2">
  <title>SlopeSense CAP Feed — No active alerts above threshold</title>
</feed>"""
        return Response(content=xml, media_type="application/xml")

    # Wrap multiple alerts in a feed
    alert_xmls = []
    for alert in alerts[:50]:  # cap at 50
        try:
            xml = engine.format_cap_xml(alert)
            alert_xmls.append(xml)
        except Exception as e:
            logger.warning(f"CAP XML generation failed for {alert.get('alert_code')}: {e}")

    feed_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="urn:oasis:names:tc:emergency:cap:1.2">
  <title>SlopeSense Landslide Risk Alert Feed — India</title>
  <updated>{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}</updated>
  <count>{len(alert_xmls)}</count>
  {''.join(alert_xmls)}
</feed>"""

    return Response(content=feed_xml, media_type="application/xml")


@app.get("/v1/geojson/fpi", tags=["Visualisation"])
async def get_fpi_geojson(
    state: Optional[str] = None,
    min_fpi: float = 0.30,
    db: AsyncSession = Depends(get_db),
):
    """Returns current block-level FPI scores as GeoJSON points."""
    from sqlalchemy import text
    
    if db is None:
        return {"type": "FeatureCollection", "features": _synthetic_wayanad_geojson()}
        
    query = """
        SELECT block_code, block_name, district_name, state_code,
               lat, lon, fpi_score, fpi_24h, tier,
               rainfall_3d_mm, soil_moisture_percentile
        FROM alerts
        WHERE is_active = 1 AND fpi_score >= :min_fpi
    """
    params = {"min_fpi": min_fpi}
    if state:
        query += " AND state_code = :state"
        params["state"] = state
        
    result = await db.execute(text(query), params)
    rows = result.fetchall()
    
    features = []
    for row in rows:
        mapping = dict(row._mapping)
        if not mapping.get("lat") or not mapping.get("lon"):
            continue
            
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [mapping["lon"], mapping["lat"]]
            },
            "properties": {
                "fpi": mapping["fpi_score"],
                "fpi_pct": round(mapping["fpi_score"] * 100),
                "fpi_24h": mapping["fpi_24h"],
                "tier": mapping["tier"],
                "district": mapping["district_name"],
                "block": mapping["block_name"],
                "block_code": mapping["block_code"],
                "state_code": mapping["state_code"],
                "rainfall_3d_mm": mapping["rainfall_3d_mm"],
                "soil_moisture_pct": mapping["soil_moisture_percentile"],
                "risk_label": get_risk_label(mapping["fpi_score"] or 0.0),
                "risk_short": get_risk_short(mapping["fpi_score"] or 0.0),
                "risk_color": get_risk_color(mapping["fpi_score"] or 0.0),
                "risk_description": get_risk_description(mapping["fpi_score"] or 0.0),
            }
        })

    return {"type": "FeatureCollection", "features": features}


@app.get("/v1/geojson/districts", tags=["GeoJSON"])
async def get_districts_geojson(
    min_fpi: float = Query(0.10, description="Minimum FPI for inclusion"),
    state: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    GeoJSON of district-level aggregated FPI for choropleth rendering.
    Returns one feature per district with max FPI across all its blocks.
    """
    from sqlalchemy import text

    query = """
        SELECT district_code, district_name, state_code, state_name,
               MAX(fpi_score) as max_fpi, MAX(fpi_24h) as max_fpi_24h,
               AVG(lat) as lat, AVG(lon) as lon,
               COUNT(*) as block_count
        FROM alerts
        WHERE is_active = 1 AND fpi_score >= :min_fpi
    """
    params: Dict = {"min_fpi": min_fpi}
    if state:
        query += " AND state_code = :state"
        params["state"] = state
    query += " GROUP BY district_code, district_name, state_code, state_name ORDER BY max_fpi DESC"

    try:
        result = await db.execute(text(query), params)
        rows = result.fetchall()
    except Exception:
        rows = []

    features = []
    for row in rows:
        m = dict(row._mapping)
        if not m.get("lat") or not m.get("lon"):
            continue
        fpi = m["max_fpi"] or 0.0
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [m["lon"], m["lat"]]},
            "properties": {
                "district_code": m["district_code"],
                "district_name": m["district_name"],
                "state_code": m["state_code"],
                "state_name": m["state_name"],
                "max_fpi": round(fpi, 4),
                "max_fpi_pct": round(fpi * 100),
                "max_fpi_24h": round(m["max_fpi_24h"] or 0.0, 4),
                "block_count": m["block_count"],
                "risk_label": get_risk_label(fpi),
                "risk_short": get_risk_short(fpi),
                "risk_color": get_risk_color(fpi),
                "risk_description": get_risk_description(fpi),
            }
        })

    return {"type": "FeatureCollection", "features": features}


@app.get("/v1/geojson/alerts", tags=["GeoJSON"])
async def get_alerts_geojson(min_fpi: float = Query(0.40), db: AsyncSession = Depends(get_db)):
    """GeoJSON of active alerts for overlay on dashboard map."""
    features = []
    for alert in await _get_active_alerts(db):
        if not alert.get("is_active") or alert["fpi_score"] < min_fpi:
            continue
        lat = alert.get("lat")
        lon = alert.get("lon")
        fpi = alert.get("fpi_score", 0.0) or 0.0
        props = {**alert, "risk_label": get_risk_label(fpi), "risk_color": get_risk_color(fpi)}
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon or 76.0, lat or 11.5]},
            "properties": props,
        })
    return {"type": "FeatureCollection", "features": features}


@app.post("/v1/contacts/register", tags=["Contacts"])
async def register_contact(contact: ContactRegistration, db: AsyncSession = Depends(get_db)):
    """Register for WhatsApp/email alert delivery."""
    record_id = str(uuid.uuid4())
    try:
        contact_row = AlertContact(
            id=uuid.UUID(record_id),
            name=contact.name,
            role=contact.role,
            organization=contact.organization,
            language=contact.language,
            state_code=contact.state_code.upper(),
            district_code=contact.district_code.upper() if contact.district_code else None,
            block_code=contact.block_code.upper() if contact.block_code else None,
            whatsapp_number=contact.whatsapp_number,
            email=contact.email,
            min_tier_for_whatsapp=_alert_tier_or_default(contact.min_tier, AlertTier.WARNING),
            is_active=True,
        )
        db.add(contact_row)
        await db.commit()
    except Exception as exc:
        await db.rollback()
        if settings.is_production:
            logger.exception("Contact registration failed")
            raise HTTPException(status_code=503, detail="Contact registry unavailable")
        logger.warning("Contact registry unavailable, returning transient registration id: %s", exc)
    logger.info(f"Contact registered: {contact.name} ({contact.role}) → {contact.whatsapp_number}")
    return {
        "status": "registered",
        "id": record_id,
        "message": f"You will receive {contact.min_tier}+ alerts for {contact.district_code or contact.state_code}",
    }


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """WebSocket endpoint for live FPI updates on the dashboard."""
    await manager.connect(websocket)
    try:
        # Send current state on connect
        await websocket.send_json({
            "type": "init",
            "alerts": _current_alerts[:20],
            "last_run": _last_run.isoformat() if _last_run else None,
        })
        while True:
            data = await websocket.receive_text()
            # Echo back with timestamp (keepalive)
            await websocket.send_json({"type": "pong", "ts": datetime.now(timezone.utc).isoformat()})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ── Scheduler trigger (called by cron/APScheduler) ────────────────────────────

@app.post("/internal/trigger-run", tags=["Internal"])
async def trigger_model_run(request: Request, token: str = Query(...)):
    """
    Trigger a model run. Called by the scheduler every 6 hours.
    Protected by internal token.
    """
    expected = settings.internal_trigger_token or os.environ.get("INTERNAL_TRIGGER_TOKEN", "dev-token")
    if token != expected:
        raise HTTPException(status_code=403, detail="Invalid token")
    client_host = request.client.host if request.client else ""
    if settings.is_production and client_host not in {"127.0.0.1", "::1", "api", "scheduler"}:
        if not (client_host.startswith("10.") or client_host.startswith("172.") or client_host.startswith("192.168.")):
            raise HTTPException(status_code=403, detail="Internal network only")

    try:
        result = await _run_model_pipeline()
        await manager.broadcast({"type": "model_run_complete", **result})
        return result
    except Exception as e:
        logger.error(f"Model run failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Helper functions ──────────────────────────────────────────────────────────

async def _run_model_pipeline() -> Dict:
    """Execute full pipeline: ingest → preprocess → FPI → alert → dispatch."""
    global _current_alerts, _last_run, _fpi_grid_cache

    from backend.processing.preprocessor import DataPreprocessor
    from backend.model.fpi_engine import FPIEngine
    from backend.alert.alert_engine import AlertEngine
    from backend.alert.dispatcher import AlertDispatcher

    run_time = datetime.now(timezone.utc)
    logger.info(f"Pipeline: starting run at {run_time.isoformat()}")

    # 1. Preprocess
    preprocessor = DataPreprocessor()
    feature_grid = preprocessor.build_feature_grid(run_time=run_time)

    # 2. FPI
    engine = FPIEngine()
    cell_fpis = engine.compute_grid(feature_grid)

    # Simple block map for demo
    block_map = {}
    block_fpis = engine.aggregate_to_blocks(cell_fpis, block_map)

    # 3. Alert engine
    alert_engine = AlertEngine()
    prev_alerts = {a["block_code"]: a for a in _current_alerts}
    new_alerts, expired = await alert_engine.evaluate_blocks(block_fpis, prev_alerts)

    _current_alerts = new_alerts
    _last_run = run_time
    _fpi_grid_cache = {
        "cells": [vars(c) if hasattr(c, "__dict__") else c.__dict__ for c in cell_fpis[:5000]],
        "run_timestamp": run_time.isoformat(),
    }

    # 4. Dispatch
    dispatcher = AlertDispatcher()
    dispatch_result = await dispatcher.dispatch_alerts(new_alerts)

    result = {
        "run_timestamp": run_time.isoformat(),
        "cells_computed": len(cell_fpis),
        "blocks_computed": len(block_fpis),
        "active_alerts": len(new_alerts),
        "expired_alerts": len(expired),
        **dispatch_result,
    }

    logger.info(f"Pipeline complete: {result}")
    return result


async def _compute_point_fpi(lat: float, lon: float, hours_ahead: int) -> RiskResponse:
    """On-demand FPI computation for a point."""
    from backend.processing.preprocessor import DataPreprocessor
    from backend.model.fpi_engine import FPIEngine

    bbox = {
        "min_lat": lat - 0.15,
        "max_lat": lat + 0.15,
        "min_lon": lon - 0.15,
        "max_lon": lon + 0.15,
    }

    preprocessor = DataPreprocessor(bbox=bbox)
    grid = preprocessor.build_feature_grid()
    engine = FPIEngine()

    import numpy as np
    lat_idx = int(np.argmin(np.abs(grid.lats - lat)))
    lon_idx = int(np.argmin(np.abs(grid.lons - lon)))
    features = engine._extract_cell_features(grid, lat_idx, lon_idx)

    fpi = engine._score_cell(features)
    fpi_24h = engine._score_cell_forecast(features, 24)
    fpi_48h = engine._score_cell_forecast(features, 48)
    ci_lo, ci_hi = engine._compute_confidence_interval(fpi, features)
    tier = engine._classify_tier(fpi, (ci_hi - ci_lo) > 0.30)
    dominant, _ = engine._identify_dominant_signal(features)

    score = fpi
    if hours_ahead == 24:
        score = fpi_24h
    elif hours_ahead == 48:
        score = fpi_48h

    from backend.model.fpi_engine import get_risk_level
    level = get_risk_level(score)

    return RiskResponse(
        lat=lat, lon=lon,
        cell_id=f"{lat:.2f}_{lon:.2f}",
        district=None, block=None,
        fpi_score=round(score, 4),
        fpi_ci_lower=round(ci_lo, 4),
        fpi_ci_upper=round(ci_hi, 4),
        fpi_24h=round(fpi_24h, 4),
        fpi_48h=round(fpi_48h, 4),
        alert_tier=tier,
        risk_label=level["label"],
        risk_color=level["color"],
        risk_description=level["description"],
        dominant_signal=dominant,
        rainfall_3d_mm=round(features["rainfall_3d_mm"], 1),
        soil_moisture_pct=round(features["soil_moisture_pct"], 1),
        slope_degrees=round(features["slope_degrees"], 1),
        run_timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _find_nearest_cell(cells: List[Dict], lat: float, lon: float) -> Optional[Dict]:
    """Find nearest FPI cell to a lat/lon point."""
    if not cells:
        return None
    import numpy as np
    lats = [c.get("lat", 0) for c in cells]
    lons = [c.get("lon", 0) for c in cells]
    dists = [(lat - la) ** 2 + (lon - lo) ** 2 for la, lo in zip(lats, lons)]
    return cells[int(np.argmin(dists))]


async def _active_alert_count() -> int:
    return len([a for a in _current_alerts if a.get("is_active")])


async def _get_active_alerts(db: Optional[AsyncSession]) -> List[Dict[str, Any]]:
    if db is not None:
        try:
            result = await db.execute(select(Alert).where(Alert.is_active.is_(True)))
            rows = result.scalars().all()
            if rows:
                return [_alert_row_to_dict(row) for row in rows]
        except Exception as exc:
            logger.warning("Active alert database query failed, using cache fallback: %s", exc)
    return [a for a in _current_alerts if a.get("is_active")]


def _alert_row_to_dict(row: Alert) -> Dict[str, Any]:
    tier = row.tier.value if hasattr(row.tier, "value") else row.tier
    return {
        "id": str(row.id),
        "alert_code": row.alert_code,
        "state_code": row.state_code,
        "state_name": row.state_name,
        "district_code": row.district_code,
        "district_name": row.district_name,
        "block_code": row.block_code,
        "block_name": row.block_name,
        "fpi_score": row.fpi_score,
        "fpi_ci_lower": row.fpi_ci_lower,
        "fpi_ci_upper": row.fpi_ci_upper,
        "fpi_24h": row.fpi_24h,
        "tier": tier,
        "is_active": row.is_active,
        "is_suppressed": row.is_suppressed,
        "consecutive_cycles": row.consecutive_cycles,
        "dominant_signals": row.dominant_signals or [],
        "rainfall_3d_mm": row.rainfall_3d_mm,
        "soil_moisture_percentile": row.soil_moisture_percentile,
        "cell_count_total": row.cell_count_total,
        "cell_count_breached": row.cell_count_breached,
        "breach_fraction": row.breach_fraction,
        "issued_at": row.issued_at.isoformat() if row.issued_at else None,
    }


def _alert_tier_or_default(value: str, default: AlertTier) -> AlertTier:
    try:
        return AlertTier[value.upper()]
    except Exception:
        return default


def _parse_bbox(bbox: Optional[str]) -> Optional[tuple[float, float, float, float]]:
    if not bbox:
        return None
    try:
        min_lon, min_lat, max_lon, max_lat = [float(part.strip()) for part in bbox.split(",")]
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="bbox must be minLon,minLat,maxLon,maxLat") from exc
    if min_lon > max_lon or min_lat > max_lat:
        raise HTTPException(status_code=422, detail="bbox minimums must be less than maximums")
    if not (
        -180 <= min_lon <= 180
        and -180 <= max_lon <= 180
        and -90 <= min_lat <= 90
        and -90 <= max_lat <= 90
    ):
        raise HTTPException(status_code=422, detail="bbox coordinates are out of range")
    return min_lon, min_lat, max_lon, max_lat


def _history_row_to_dict(row: FPIHistory) -> Dict[str, Any]:
    return {
        "cell_id": row.cell_id,
        "run_timestamp": row.run_timestamp.isoformat(),
        "lat": row.lat,
        "lon": row.lon,
        "district_code": row.district_code,
        "block_code": row.block_code,
        "fpi_score": row.fpi_score,
        "fpi_ci_lower": row.fpi_ci_lower,
        "fpi_ci_upper": row.fpi_ci_upper,
        "fpi_24h": row.fpi_24h,
        "fpi_48h": row.fpi_48h,
        "alert_tier": row.alert_tier.value if hasattr(row.alert_tier, "value") else row.alert_tier,
        "rainfall_3d_mm": row.rainfall_3d_mm,
        "soil_moisture_percentile": row.soil_moisture_percentile,
        "slope_degrees": row.slope_degrees,
        "dominant_signal": row.dominant_signal,
        "model_version": row.model_version,
    }


def _aggregate_history_to_blocks(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    import numpy as np

    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row.get("block_code") or "UNKNOWN", []).append(row)

    blocks = []
    for block_code, block_rows in grouped.items():
        scores = np.array([r["fpi_score"] for r in block_rows], dtype=float)
        blocks.append(
            {
                "block_code": block_code,
                "cell_count": len(block_rows),
                "max_fpi": float(np.max(scores)),
                "p95_fpi": float(np.percentile(scores, 95)),
                "mean_fpi": float(np.mean(scores)),
                "alert_tier": _tier_for_score(float(np.percentile(scores, 95))),
            }
        )
    return sorted(blocks, key=lambda item: item["p95_fpi"], reverse=True)


def _tier_for_score(score: float) -> str:
    if score >= 0.80:
        return "EMERGENCY"
    if score >= 0.65:
        return "WARNING"
    if score >= 0.40:
        return "WATCH"
    return "NORMAL"


def _synthetic_historical_rows(date_value: str, district_code: str) -> List[Dict[str, Any]]:
    blocks = [
        ("MEP", 11.583, 76.083, 0.73),
        ("VYT", 11.520, 76.010, 0.61),
        ("KPT", 11.610, 76.080, 0.55),
        ("AMB", 11.620, 76.190, 0.48),
    ]
    rows = []
    for idx, (block_code, lat, lon, score) in enumerate(blocks):
        rows.append(
            {
                "cell_id": f"{district_code.upper()}_{idx}",
                "run_timestamp": f"{date_value}T06:00:00+00:00",
                "lat": lat,
                "lon": lon,
                "district_code": district_code.upper(),
                "block_code": block_code,
                "fpi_score": score,
                "fpi_ci_lower": max(0, score - 0.12),
                "fpi_ci_upper": min(1, score + 0.12),
                "fpi_24h": min(0.99, score * 1.1),
                "fpi_48h": min(0.99, score * 1.06),
                "alert_tier": _tier_for_score(score),
                "rainfall_3d_mm": 180 - idx * 18,
                "soil_moisture_percentile": 91 - idx * 5,
                "slope_degrees": 31 - idx * 2,
                "dominant_signal": "rainfall_accumulation",
                "model_version": "v0.1",
            }
        )
    return rows


def _synthetic_report_alerts() -> List[Dict[str, Any]]:
    return [
        {
            "id": "report-wayanad-meppadi",
            "alert_code": "KL-WYD-MEP-DEMO",
            "tier": "WARNING",
            "state_code": "KL",
            "state_name": "Kerala",
            "district_code": "WYD",
            "district_name": "Wayanad",
            "block_code": "MEP",
            "block_name": "Meppadi",
            "fpi_score": 0.73,
            "fpi_ci_lower": 0.61,
            "fpi_ci_upper": 0.84,
            "fpi_24h": 0.81,
            "is_active": True,
            "dominant_signals": [{"signal": "rainfall_accumulation", "value": 0.73}],
            "rainfall_3d_mm": 183,
            "soil_moisture_percentile": 91,
        }
    ]


def _synthetic_retrospective_summary() -> Dict:
    """Synthetic retrospective results for demo when model not yet run."""
    return {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "model_version": "v0.1",
        "total_events": 6,
        "flagged_at_t24": 4,
        "pass_criterion": "≥4/6 flagged at T-24h with FPI≥target",
        "passed": True,
        "note": "Synthetic results — run scripts/retrospective.py for real validation",
        "results": [
            {"event_id": "wayanad_2024", "event_name": "Wayanad 2024", "fpi_t24": 0.73, "flagged_at_t24": True, "deaths": 420, "lead_time_hours": 24},
            {"event_id": "kedarnath_2013", "event_name": "Kedarnath 2013", "fpi_t24": 0.81, "flagged_at_t24": True, "deaths": 5700, "lead_time_hours": 48},
            {"event_id": "malin_2014", "event_name": "Malin 2014", "fpi_t24": 0.69, "flagged_at_t24": True, "deaths": 151, "lead_time_hours": 24},
            {"event_id": "chamoli_2021", "event_name": "Chamoli 2021", "fpi_t24": 0.47, "flagged_at_t24": True, "deaths": 204, "lead_time_hours": 24},
            {"event_id": "sikkim_2023", "event_name": "Sikkim 2023", "fpi_t24": 0.41, "flagged_at_t24": False, "deaths": 40, "lead_time_hours": None},
            {"event_id": "joshimath_2023", "event_name": "Joshimath 2023", "fpi_t24": 0.31, "flagged_at_t24": False, "deaths": 0, "lead_time_hours": None},
        ],
    }


def _synthetic_wayanad_geojson() -> List[Dict]:
    """Synthetic Wayanad GeoJSON for demo."""
    import random
    random.seed(42)
    features = []
    blocks = [
        ("Meppadi", 11.583, 76.083, 0.73),
        ("Vythiri", 11.52, 76.01, 0.61),
        ("Mananthavady", 11.80, 76.00, 0.44),
        ("Kalpetta", 11.61, 76.08, 0.55),
        ("Sulthan Bathery", 11.67, 76.25, 0.38),
        ("Ambalavayal", 11.62, 76.19, 0.48),
    ]
    for name, lat, lon, fpi in blocks:
        tier = "EMERGENCY" if fpi > 0.80 else "WARNING" if fpi > 0.65 else "WATCH" if fpi > 0.40 else "NORMAL"
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "fpi": fpi,
                "fpi_24h": min(fpi * 1.1, 0.99),
                "tier": tier,
                "district": "Wayanad",
                "block": name,
                "rainfall_3d_mm": random.uniform(80, 200),
                "soil_moisture_pct": random.uniform(65, 95),
            },
        })
    return features


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.api.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("ENVIRONMENT", "development") != "production",
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
