"""
SlopeSense — Database Migration Script

Creates all tables with PostGIS spatial extensions.
Run: python -m scripts.migrate
"""

import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DDL = """
-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enum types
DO $$ BEGIN
    CREATE TYPE alert_tier AS ENUM ('NORMAL','WATCH','WARNING','EMERGENCY','MONITORING');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE delivery_channel AS ENUM ('WHATSAPP','EMAIL','SMS','CAP_FEED');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE delivery_status AS ENUM ('PENDING','SENT','DELIVERED','FAILED','READ');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Districts reference table
CREATE TABLE IF NOT EXISTS districts (
    id               SERIAL PRIMARY KEY,
    state_code       VARCHAR(8) NOT NULL,
    state_name       VARCHAR(64) NOT NULL,
    district_code    VARCHAR(16) NOT NULL UNIQUE,
    district_name    VARCHAR(64) NOT NULL,
    block_code       VARCHAR(24),
    block_name       VARCHAR(64),
    geom             GEOMETRY(MULTIPOLYGON, 4326),
    centroid_lat     FLOAT,
    centroid_lon     FLOAT,
    is_high_risk     BOOLEAN DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS ix_districts_state ON districts(state_code);
CREATE INDEX IF NOT EXISTS ix_districts_code ON districts(district_code);

-- Current FPI grid (hot store — upserted each run)
CREATE TABLE IF NOT EXISTS fpi_grid (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cell_id               VARCHAR(32) NOT NULL UNIQUE,
    lat                   FLOAT NOT NULL,
    lon                   FLOAT NOT NULL,
    geom                  GEOMETRY(POINT, 4326) NOT NULL,
    state_code            VARCHAR(8),
    district_code         VARCHAR(16),
    block_code            VARCHAR(24),
    fpi_score             FLOAT NOT NULL,
    fpi_ci_lower          FLOAT NOT NULL,
    fpi_ci_upper          FLOAT NOT NULL,
    fpi_24h               FLOAT,
    fpi_48h               FLOAT,
    alert_tier            alert_tier DEFAULT 'NORMAL',
    rainfall_3d_mm        FLOAT,
    rainfall_24h_forecast_mm FLOAT,
    soil_moisture_percentile FLOAT,
    slope_degrees         FLOAT,
    ndvi_delta            FLOAT,
    susceptibility_class  INTEGER,
    lithology_class       VARCHAR(32),
    dominant_signal       VARCHAR(64),
    model_version         VARCHAR(16) DEFAULT 'v0.1',
    run_timestamp         TIMESTAMPTZ NOT NULL,
    created_at            TIMESTAMPTZ DEFAULT NOW(),
    updated_at            TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_fpi_grid_cell ON fpi_grid(cell_id);
CREATE INDEX IF NOT EXISTS ix_fpi_grid_district ON fpi_grid(district_code, run_timestamp);
CREATE INDEX IF NOT EXISTS ix_fpi_grid_score ON fpi_grid(fpi_score);
CREATE INDEX IF NOT EXISTS ix_fpi_grid_geom ON fpi_grid USING GIST(geom);

-- Historical FPI (immutable audit log)
CREATE TABLE IF NOT EXISTS fpi_history (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cell_id           VARCHAR(32) NOT NULL,
    run_timestamp     TIMESTAMPTZ NOT NULL,
    lat               FLOAT NOT NULL,
    lon               FLOAT NOT NULL,
    district_code     VARCHAR(16),
    block_code        VARCHAR(24),
    fpi_score         FLOAT NOT NULL,
    fpi_ci_lower      FLOAT NOT NULL,
    fpi_ci_upper      FLOAT NOT NULL,
    fpi_24h           FLOAT,
    fpi_48h           FLOAT,
    alert_tier        alert_tier,
    rainfall_3d_mm    FLOAT,
    soil_moisture_percentile FLOAT,
    slope_degrees     FLOAT,
    dominant_signal   VARCHAR(64),
    model_version     VARCHAR(16) DEFAULT 'v0.1'
);
CREATE INDEX IF NOT EXISTS ix_fpi_hist_cell_time ON fpi_history(cell_id, run_timestamp);
CREATE INDEX IF NOT EXISTS ix_fpi_hist_district ON fpi_history(district_code, run_timestamp);

-- Alerts (block-level aggregated)
CREATE TABLE IF NOT EXISTS alerts (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_code            VARCHAR(64) NOT NULL UNIQUE,
    state_code            VARCHAR(8) NOT NULL,
    state_name            VARCHAR(64) NOT NULL,
    district_code         VARCHAR(16) NOT NULL,
    district_name         VARCHAR(64) NOT NULL,
    block_code            VARCHAR(24),
    block_name            VARCHAR(64),
    fpi_score             FLOAT NOT NULL,
    fpi_ci_lower          FLOAT NOT NULL,
    fpi_ci_upper          FLOAT NOT NULL,
    fpi_24h               FLOAT,
    cell_count_total      INTEGER,
    cell_count_breached   INTEGER,
    breach_fraction       FLOAT,
    tier                  alert_tier NOT NULL,
    is_active             BOOLEAN DEFAULT TRUE,
    is_suppressed         BOOLEAN DEFAULT FALSE,
    consecutive_cycles    INTEGER DEFAULT 1,
    dominant_signals      JSONB,
    rainfall_3d_mm        FLOAT,
    soil_moisture_percentile FLOAT,
    validated             BOOLEAN,
    validated_at          TIMESTAMPTZ,
    validation_source     VARCHAR(128),
    validation_notes      TEXT,
    issued_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at            TIMESTAMPTZ,
    cleared_at            TIMESTAMPTZ,
    updated_at            TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_alerts_active_tier ON alerts(is_active, tier);
CREATE INDEX IF NOT EXISTS ix_alerts_district ON alerts(district_code, is_active);
CREATE INDEX IF NOT EXISTS ix_alerts_issued ON alerts(issued_at DESC);

-- Alert contacts registry
CREATE TABLE IF NOT EXISTS alert_contacts (
    id                        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                      VARCHAR(128) NOT NULL,
    role                      VARCHAR(64) NOT NULL,
    organization              VARCHAR(128),
    language                  VARCHAR(8) DEFAULT 'hi',
    state_code                VARCHAR(8) NOT NULL,
    district_code             VARCHAR(16),
    block_code                VARCHAR(24),
    whatsapp_number           VARCHAR(20),
    email                     VARCHAR(256),
    phone                     VARCHAR(20),
    min_tier_for_whatsapp     alert_tier DEFAULT 'WARNING',
    min_tier_for_email        alert_tier DEFAULT 'WATCH',
    is_active                 BOOLEAN DEFAULT TRUE,
    registered_at             TIMESTAMPTZ DEFAULT NOW(),
    updated_at                TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_contacts_district ON alert_contacts(district_code, is_active);
CREATE INDEX IF NOT EXISTS ix_contacts_state ON alert_contacts(state_code, is_active);

-- Alert deliveries audit log
CREATE TABLE IF NOT EXISTS alert_deliveries (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_id              UUID REFERENCES alerts(id),
    contact_id            UUID REFERENCES alert_contacts(id),
    channel               delivery_channel NOT NULL,
    recipient             VARCHAR(256) NOT NULL,
    language              VARCHAR(8) DEFAULT 'en',
    message_body          TEXT NOT NULL,
    status                delivery_status DEFAULT 'PENDING',
    external_message_id   VARCHAR(128),
    error_detail          TEXT,
    sent_at               TIMESTAMPTZ,
    delivered_at          TIMESTAMPTZ,
    read_at               TIMESTAMPTZ,
    feedback_received     BOOLEAN DEFAULT FALSE,
    feedback_at           TIMESTAMPTZ,
    feedback_text         VARCHAR(256)
);
CREATE INDEX IF NOT EXISTS ix_deliveries_alert ON alert_deliveries(alert_id);
CREATE INDEX IF NOT EXISTS ix_deliveries_status ON alert_deliveries(status);

-- Confirmed landslide events
CREATE TABLE IF NOT EXISTS landslide_events (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_name            VARCHAR(128) NOT NULL,
    source                VARCHAR(64) NOT NULL,
    source_id             VARCHAR(64),
    lat                   FLOAT NOT NULL,
    lon                   FLOAT NOT NULL,
    geom                  GEOMETRY(POINT, 4326) NOT NULL,
    district_code         VARCHAR(16),
    block_code            VARCHAR(24),
    location_description  TEXT,
    event_date            TIMESTAMPTZ NOT NULL,
    deaths                INTEGER,
    injuries              INTEGER,
    displacement          INTEGER,
    economic_damage_cr    FLOAT,
    trigger               VARCHAR(64),
    notes                 TEXT,
    was_flagged_24h       BOOLEAN,
    was_flagged_48h       BOOLEAN,
    fpi_at_t24            FLOAT,
    fpi_at_t12            FLOAT,
    fpi_at_t6             FLOAT,
    validation_notes      TEXT,
    created_at            TIMESTAMPTZ DEFAULT NOW(),
    updated_at            TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_events_date ON landslide_events(event_date DESC);
CREATE INDEX IF NOT EXISTS ix_events_district ON landslide_events(district_code);
CREATE INDEX IF NOT EXISTS ix_events_geom ON landslide_events USING GIST(geom);

-- Retrospective validation results
CREATE TABLE IF NOT EXISTS retrospective_results (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id              VARCHAR(64) NOT NULL,
    event_name            VARCHAR(128) NOT NULL,
    model_version         VARCHAR(16) NOT NULL,
    run_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fpi_t72               FLOAT,
    fpi_t48               FLOAT,
    fpi_t24               FLOAT,
    fpi_t12               FLOAT,
    fpi_t6                FLOAT,
    fpi_at_event          FLOAT,
    target_fpi            FLOAT,
    flagged_at_t24        BOOLEAN,
    lead_time_hours       FLOAT,
    data_source           VARCHAR(32),
    notes                 TEXT
);
CREATE INDEX IF NOT EXISTS ix_retro_event ON retrospective_results(event_id, run_at DESC);

-- Auto-update updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$ BEGIN
    CREATE TRIGGER alerts_updated_at BEFORE UPDATE ON alerts
        FOR EACH ROW EXECUTE FUNCTION update_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TRIGGER contacts_updated_at BEFORE UPDATE ON alert_contacts
        FOR EACH ROW EXECUTE FUNCTION update_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
"""

SEED_HIGH_RISK_DISTRICTS = """
INSERT INTO districts (state_code, state_name, district_code, district_name, block_code, block_name, centroid_lat, centroid_lon, is_high_risk)
VALUES
  ('KL','Kerala','KL_WYD','Wayanad','KL_WYD_MEP','Meppadi',11.583,76.083,TRUE),
  ('KL','Kerala','KL_WYD','Wayanad','KL_WYD_VYT','Vythiri',11.520,76.010,TRUE),
  ('KL','Kerala','KL_IDK','Idukki','KL_IDK_MUN','Munnar',10.088,77.059,TRUE),
  ('UK','Uttarakhand','UK_CHA','Chamoli','UK_CHA_TAP','Tapovan',30.470,79.720,TRUE),
  ('UK','Uttarakhand','UK_RUD','Rudraprayag','UK_RUD_KED','Ukhimath',30.735,79.067,TRUE),
  ('UK','Uttarakhand','UK_UHK','Uttarkashi','UK_UHK_GAN','Gangotri',30.995,78.939,TRUE),
  ('SK','Sikkim','SK_MAN','Mangan','SK_MAN_LAC','Lachen',27.590,88.530,TRUE),
  ('SK','Sikkim','SK_EAS','East Sikkim','SK_EAS_GAN','Gangtok',27.329,88.612,TRUE),
  ('MH','Maharashtra','MH_PUN','Pune','MH_PUN_AMB','Ambegaon',19.050,73.650,TRUE),
  ('HP','Himachal Pradesh','HP_MND','Mandi','HP_MND_KUL','Kulu',31.957,77.109,TRUE),
  ('MG','Meghalaya','MG_EKH','East Khasi Hills','MG_EKH_CHE','Cherrapunji',25.284,91.727,TRUE),
  ('KA','Karnataka','KA_CDK','Kodagu','KA_CDK_MAD','Madikeri',12.418,75.738,TRUE)
ON CONFLICT (district_code) DO NOTHING;
"""

SEED_HISTORICAL_EVENTS = """
INSERT INTO landslide_events (event_name, source, lat, lon, geom, district_code, event_date, deaths, injuries, economic_damage_cr, trigger, notes)
VALUES
  ('Wayanad Landslide 2024','NDMA',11.583,76.083,ST_SetSRID(ST_MakePoint(76.083,11.583),4326),'KL_WYD','2024-07-30 02:17:00+05:30',420,397,1200,'rainfall','Deadliest landslide in Kerala history. Hume Centre warning 16h prior not integrated.'),
  ('Sikkim GLOF 2023','NASA_GLC',27.59,88.53,ST_SetSRID(ST_MakePoint(88.53,27.59),4326),'SK_MAN','2023-10-04 01:30:00+05:30',40,76,300,'GLOF','South Lhonak glacial lake outburst flood.'),
  ('Chamoli Disaster 2021','NDMA',30.47,79.72,ST_SetSRID(ST_MakePoint(79.72,30.47),4326),'UK_CHA','2021-02-07 10:50:00+05:30',204,25,450,'rock_ice_avalanche','Ronti peak rock-ice detachment. Rishiganga hydropower plant destroyed.'),
  ('Malin Village 2014','NDMA',19.05,73.65,ST_SetSRID(ST_MakePoint(73.65,19.05),4326),'MH_PUN','2014-07-30 06:30:00+05:30',151,45,50,'rainfall','350mm 3-day rainfall on deforested slope.'),
  ('Kedarnath 2013','NDMA',30.735,79.067,ST_SetSRID(ST_MakePoint(79.067,30.735),4326),'UK_RUD','2013-06-16 20:00:00+05:30',5700,5000,10000,'rainfall','India worst modern natural disaster. 375mm in 3 days.')
ON CONFLICT DO NOTHING;
"""


def run_migration():
    """Execute DDL and seed data."""
    import psycopg2

    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://slopesense:slopesense@localhost:5432/slopesense"
    )

    logger.info(f"Connecting to: {db_url.split('@')[1] if '@' in db_url else db_url}")

    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()

        logger.info("Running DDL migrations...")
        cur.execute(DDL)
        logger.info("DDL complete.")

        logger.info("Seeding high-risk districts...")
        cur.execute(SEED_HIGH_RISK_DISTRICTS)
        logger.info("Districts seeded.")

        logger.info("Seeding historical events...")
        cur.execute(SEED_HISTORICAL_EVENTS)
        logger.info("Historical events seeded.")

        cur.close()
        conn.close()
        logger.info("Migration complete.")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    run_migration()
