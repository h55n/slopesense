"""
SlopeSense — Application Configuration
Loaded from environment variables / .env file
"""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Optional
import os


class Settings(BaseSettings):
    # ── Application ──────────────────────────────────────────────────────────
    environment: str = "development"
    secret_key: str = "dev-secret-change-in-production"
    internal_trigger_token: str = "dev-token"
    api_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    allowed_hosts: str = "localhost,127.0.0.1"
    api_keys: str = ""

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "postgresql://slopesense:slopesense@localhost:5432/slopesense"
    redis_url: str = "redis://localhost:6379/0"

    # ── NASA Earthdata ───────────────────────────────────────────────────────
    nasa_earthdata_username: Optional[str] = None
    nasa_earthdata_password: Optional[str] = None

    # ── ESA Copernicus ───────────────────────────────────────────────────────
    copernicus_client_id: Optional[str] = None
    copernicus_client_secret: Optional[str] = None

    # ── NOAA GFS ─────────────────────────────────────────────────────────────
    noaa_gfs_base_url: str = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"

    # ── WhatsApp ─────────────────────────────────────────────────────────────
    whatsapp_api_token: Optional[str] = None
    whatsapp_phone_number_id: Optional[str] = None
    whatsapp_from_number: Optional[str] = None
    whatsapp_verify_token: str = "dev-whatsapp-verify-token"
    whatsapp_app_secret: Optional[str] = None

    # ── IMD QPF (Plan A — needs MoU) ─────────────────────────────────────────
    imd_qpf_enabled: bool = False
    imd_qpf_api_url: Optional[str] = None
    imd_qpf_api_key: Optional[str] = None

    # ── Object Storage ───────────────────────────────────────────────────────
    s3_bucket: str = "slopesense-data"
    s3_endpoint_url: Optional[str] = None
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "ap-south-1"

    # ── Alert Thresholds ─────────────────────────────────────────────────────
    fpi_watch_threshold: float = 0.40
    fpi_warning_threshold: float = 0.65
    fpi_emergency_threshold: float = 0.80
    alert_temporal_persistence_cycles: int = 2
    alert_spatial_cluster_fraction: float = 0.30
    confidence_suppression_width: float = 0.30

    # ── Scheduler ────────────────────────────────────────────────────────────
    model_run_interval_hours: int = 6
    sentinel2_fetch_interval_days: int = 5

    model_config = {"env_file": ".env", "case_sensitive": False, "protected_namespaces": ()}

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def async_database_url(self) -> str:
        if self.database_url.startswith("postgresql+asyncpg://"):
            return self.database_url
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if self.database_url.startswith("sqlite+aiosqlite://"):
            return self.database_url
        if self.database_url.startswith("sqlite://"):
            return self.database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        return self.database_url

    @property
    def allowed_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def allowed_host_list(self) -> List[str]:
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]

    @property
    def api_key_list(self) -> List[str]:
        return [key.strip() for key in self.api_keys.split(",") if key.strip()]

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, value: str):
        environment = os.getenv("ENVIRONMENT", "development")
        if environment == "production" and len(value or "") < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters in production")
        return value


settings = Settings()
