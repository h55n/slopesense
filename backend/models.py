"""
SlopeSense — Database Models (SQLAlchemy + PostGIS)

Tables:
  fpi_grid          — Current FPI scores per 1km² cell
  fpi_history       — Historical FPI runs (for retrospective + audit)
  alerts            — Generated alerts (block-level aggregated)
  alert_contacts    — Registered DDMA/block officers and Aapda Mitra volunteers
  alert_deliveries  — Audit log of every WhatsApp/email message sent
  events            — Confirmed landslide events (from NASA GLC + NDMA)
  districts         — District/block/state reference table
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column, Integer, Float, String, Boolean, DateTime,
    Text, JSON, ForeignKey, Index, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship
from geoalchemy2 import Geometry
import uuid
import enum


class Base(DeclarativeBase):
    pass


class AlertTier(str, enum.Enum):
    NORMAL = "NORMAL"
    WATCH = "WATCH"
    WARNING = "WARNING"
    EMERGENCY = "EMERGENCY"
    MONITORING = "MONITORING"  # suppressed — high uncertainty


class DeliveryChannel(str, enum.Enum):
    WHATSAPP = "WHATSAPP"
    EMAIL = "EMAIL"
    SMS = "SMS"
    CAP_FEED = "CAP_FEED"


class DeliveryStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    READ = "READ"


# ─── Geographic Reference ────────────────────────────────────────────────────

class District(Base):
    """State → District → Block hierarchy reference table."""
    __tablename__ = "districts"

    id = Column(Integer, primary_key=True)
    state_code = Column(String(8), nullable=False, index=True)
    state_name = Column(String(64), nullable=False)
    district_code = Column(String(16), nullable=False, unique=True, index=True)
    district_name = Column(String(64), nullable=False)
    block_code = Column(String(24), nullable=True, index=True)
    block_name = Column(String(64), nullable=True)
    geom = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)
    centroid_lat = Column(Float, nullable=True)
    centroid_lon = Column(Float, nullable=True)
    is_high_risk = Column(Boolean, default=False)  # flagged in NDMA NLSM

    __table_args__ = (
        Index("ix_districts_state_district", "state_code", "district_code"),
    )


# ─── FPI Grid ─────────────────────────────────────────────────────────────────

class FPIGrid(Base):
    """
    Current (most recent) FPI score per 1km² grid cell.
    One row per cell — upserted on each model run.
    """
    __tablename__ = "fpi_grid"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cell_id = Column(String(32), nullable=False, unique=True, index=True)

    # Location
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    geom = Column(Geometry("POINT", srid=4326), nullable=False)

    # Administrative
    state_code = Column(String(8), nullable=True, index=True)
    district_code = Column(String(16), nullable=True, index=True)
    block_code = Column(String(24), nullable=True, index=True)

    # FPI scores
    fpi_score = Column(Float, nullable=False)           # 0.0 – 1.0
    fpi_ci_lower = Column(Float, nullable=False)        # confidence interval lower
    fpi_ci_upper = Column(Float, nullable=False)        # confidence interval upper
    fpi_24h = Column(Float, nullable=True)              # forecast +24h
    fpi_48h = Column(Float, nullable=True)              # forecast +48h
    alert_tier = Column(SAEnum(AlertTier), default=AlertTier.NORMAL)

    # Input signals
    rainfall_3d_mm = Column(Float, nullable=True)
    rainfall_24h_forecast_mm = Column(Float, nullable=True)
    soil_moisture_percentile = Column(Float, nullable=True)  # 0–100
    slope_degrees = Column(Float, nullable=True)
    ndvi_delta = Column(Float, nullable=True)            # 10-day NDVI change
    susceptibility_class = Column(Integer, nullable=True)  # 1–5 from NDMA NLSM
    lithology_class = Column(String(32), nullable=True)

    # Dominant signal driving the score
    dominant_signal = Column(String(64), nullable=True)

    # Metadata
    model_version = Column(String(16), default="v0.1")
    run_timestamp = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_fpi_grid_location", "lat", "lon"),
        Index("ix_fpi_grid_district", "district_code", "run_timestamp"),
        Index("ix_fpi_grid_score", "fpi_score"),
    )


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(128), nullable=False)
    email = Column(String(128), nullable=False, index=True)
    organization = Column(String(128), nullable=True)
    tier = Column(String(32), default="public")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class FPIHistory(Base):
    """
    Immutable historical record — every model run kept for retrospective audit.
    """
    __tablename__ = "fpi_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cell_id = Column(String(32), nullable=False, index=True)
    run_timestamp = Column(DateTime, nullable=False, index=True)

    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    district_code = Column(String(16), nullable=True, index=True)
    block_code = Column(String(24), nullable=True)

    fpi_score = Column(Float, nullable=False)
    fpi_ci_lower = Column(Float, nullable=False)
    fpi_ci_upper = Column(Float, nullable=False)
    fpi_24h = Column(Float, nullable=True)
    fpi_48h = Column(Float, nullable=True)
    alert_tier = Column(SAEnum(AlertTier))

    rainfall_3d_mm = Column(Float, nullable=True)
    soil_moisture_percentile = Column(Float, nullable=True)
    slope_degrees = Column(Float, nullable=True)
    dominant_signal = Column(String(64), nullable=True)

    model_version = Column(String(16), default="v0.1")

    __table_args__ = (
        Index("ix_fpi_history_cell_time", "cell_id", "run_timestamp"),
        Index("ix_fpi_history_district_time", "district_code", "run_timestamp"),
    )


# ─── Pipeline Logs ────────────────────────────────────────────────────────────

class PipelineRunLog(Base):
    """
    Log of every pipeline run to track success, failure, and execution time.
    """
    __tablename__ = "pipeline_run_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    status = Column(String(32), nullable=False)  # "RUNNING", "SUCCESS", "FAILED"
    records_processed = Column(Integer, nullable=True)
    alerts_generated = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    duration_seconds = Column(Float, nullable=True)



# ─── Alerts ───────────────────────────────────────────────────────────────────

class Alert(Base):
    """
    Block-level aggregated alert. Generated by spatial clustering of FPI cells.
    """
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_code = Column(String(32), nullable=False, unique=True, index=True)

    # Location
    state_code = Column(String(8), nullable=False, index=True)
    state_name = Column(String(64), nullable=False)
    district_code = Column(String(16), nullable=False, index=True)
    district_name = Column(String(64), nullable=False)
    block_code = Column(String(24), nullable=True)
    block_name = Column(String(64), nullable=True)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)

    # Aggregated scores
    fpi_score = Column(Float, nullable=False)         # block-level aggregate (95th percentile of cells)
    fpi_ci_lower = Column(Float, nullable=False)
    fpi_ci_upper = Column(Float, nullable=False)
    fpi_24h = Column(Float, nullable=True)
    cell_count_total = Column(Integer, nullable=True)
    cell_count_breached = Column(Integer, nullable=True)
    breach_fraction = Column(Float, nullable=True)

    # Alert classification
    tier = Column(SAEnum(AlertTier), nullable=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    is_suppressed = Column(Boolean, default=False)   # suppressed due to high uncertainty
    consecutive_cycles = Column(Integer, default=1)  # for temporal persistence check

    # Signal breakdown
    dominant_signals = Column(JSON, nullable=True)   # [{"signal": "rainfall", "value": 183, "unit": "mm"}]
    rainfall_3d_mm = Column(Float, nullable=True)
    soil_moisture_percentile = Column(Float, nullable=True)

    # Audit fields
    validated = Column(Boolean, nullable=True)       # null = unverified, True = confirmed event, False = false alarm
    validated_at = Column(DateTime, nullable=True)
    validation_source = Column(String(128), nullable=True)
    validation_notes = Column(Text, nullable=True)

    # Timestamps
    issued_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    expires_at = Column(DateTime, nullable=True)
    cleared_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    deliveries = relationship("AlertDelivery", back_populates="alert")

    __table_args__ = (
        Index("ix_alerts_active_tier", "is_active", "tier"),
        Index("ix_alerts_district_active", "district_code", "is_active"),
    )


# ─── Contacts ────────────────────────────────────────────────────────────────

class AlertContact(Base):
    """
    Registered contacts for WhatsApp/email alert delivery.
    Includes district collectors, DDMA officers, Gram Pradhans, Aapda Mitra volunteers.
    """
    __tablename__ = "alert_contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(128), nullable=False)
    role = Column(String(64), nullable=False)         # "district_collector", "gram_pradhan", etc.
    organization = Column(String(128), nullable=True)
    language = Column(String(8), default="hi")        # hi, ml, kn, mr, bn, ta, en

    # Geographic scope
    state_code = Column(String(8), nullable=False, index=True)
    district_code = Column(String(16), nullable=True, index=True)
    block_code = Column(String(24), nullable=True)

    # Contact channels
    whatsapp_number = Column(String(20), nullable=True)
    email = Column(String(256), nullable=True)
    phone = Column(String(20), nullable=True)

    # Subscription settings
    min_tier_for_whatsapp = Column(SAEnum(AlertTier), default=AlertTier.WARNING)
    min_tier_for_email = Column(SAEnum(AlertTier), default=AlertTier.WATCH)
    is_active = Column(Boolean, default=True)

    # Timestamps
    registered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_contacts_district", "district_code", "is_active"),
    )


class AlertDelivery(Base):
    """
    Audit log of every alert message sent — every channel, every delivery attempt.
    """
    __tablename__ = "alert_deliveries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id = Column(UUID(as_uuid=True), ForeignKey("alerts.id"), nullable=False, index=True)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("alert_contacts.id"), nullable=True)

    channel = Column(SAEnum(DeliveryChannel), nullable=False)
    recipient = Column(String(256), nullable=False)   # phone number or email
    language = Column(String(8), default="en")
    message_body = Column(Text, nullable=False)

    status = Column(SAEnum(DeliveryStatus), default=DeliveryStatus.PENDING, index=True)
    external_message_id = Column(String(128), nullable=True)  # WhatsApp message ID
    error_detail = Column(Text, nullable=True)

    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)

    # Feedback — block officer can reply "NO EVENT" to mark false alarm
    feedback_received = Column(Boolean, default=False)
    feedback_at = Column(DateTime, nullable=True)
    feedback_text = Column(String(256), nullable=True)

    alert = relationship("Alert", back_populates="deliveries")


# ─── Confirmed Events ─────────────────────────────────────────────────────────

class LandslideEvent(Base):
    """
    Ground-truth landslide events from NASA GLC, NDMA inventory, and news sources.
    Used for retrospective validation and model calibration.
    """
    __tablename__ = "landslide_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_name = Column(String(128), nullable=False)
    source = Column(String(64), nullable=False)         # "NASA_GLC", "NDMA", "news"
    source_id = Column(String(64), nullable=True)

    # Location
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    geom = Column(Geometry("POINT", srid=4326), nullable=False)
    district_code = Column(String(16), nullable=True, index=True)
    block_code = Column(String(24), nullable=True)
    location_description = Column(Text, nullable=True)

    # Event details
    event_date = Column(DateTime, nullable=False, index=True)
    deaths = Column(Integer, nullable=True)
    injuries = Column(Integer, nullable=True)
    displacement = Column(Integer, nullable=True)
    economic_damage_cr = Column(Float, nullable=True)   # crores INR
    trigger = Column(String(64), nullable=True)         # "rainfall", "earthquake", "GLOF"
    notes = Column(Text, nullable=True)

    # Retrospective validation
    was_flagged_24h = Column(Boolean, nullable=True)    # did model flag >65% at T-24h?
    was_flagged_48h = Column(Boolean, nullable=True)
    fpi_at_t24 = Column(Float, nullable=True)           # model score at T-24h
    fpi_at_t12 = Column(Float, nullable=True)
    fpi_at_t6 = Column(Float, nullable=True)
    validation_notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_events_date_district", "event_date", "district_code"),
    )
