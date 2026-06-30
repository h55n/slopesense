"""initial_models

Revision ID: c84f95aa1b65
Revises: 
Create Date: 2026-06-22 20:04:05.501609

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2

# revision identifiers, used by Alembic.
revision: str = 'c84f95aa1b65'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis_topology")
    op.create_table('alert_contacts',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('role', sa.String(length=64), nullable=False),
    sa.Column('organization', sa.String(length=128), nullable=True),
    sa.Column('language', sa.String(length=8), nullable=True),
    sa.Column('state_code', sa.String(length=8), nullable=False),
    sa.Column('district_code', sa.String(length=16), nullable=True),
    sa.Column('block_code', sa.String(length=24), nullable=True),
    sa.Column('whatsapp_number', sa.String(length=20), nullable=True),
    sa.Column('email', sa.String(length=256), nullable=True),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.Column('min_tier_for_whatsapp', sa.Enum('NORMAL', 'WATCH', 'WARNING', 'EMERGENCY', 'MONITORING', name='alerttier'), nullable=True),
    sa.Column('min_tier_for_email', sa.Enum('NORMAL', 'WATCH', 'WARNING', 'EMERGENCY', 'MONITORING', name='alerttier'), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('registered_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alert_contacts_district_code'), 'alert_contacts', ['district_code'], unique=False)
    op.create_index(op.f('ix_alert_contacts_state_code'), 'alert_contacts', ['state_code'], unique=False)
    op.create_index('ix_contacts_district', 'alert_contacts', ['district_code', 'is_active'], unique=False)
    op.create_table('alerts',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('alert_code', sa.String(length=32), nullable=False),
    sa.Column('state_code', sa.String(length=8), nullable=False),
    sa.Column('state_name', sa.String(length=64), nullable=False),
    sa.Column('district_code', sa.String(length=16), nullable=False),
    sa.Column('district_name', sa.String(length=64), nullable=False),
    sa.Column('block_code', sa.String(length=24), nullable=True),
    sa.Column('block_name', sa.String(length=64), nullable=True),
    sa.Column('fpi_score', sa.Float(), nullable=False),
    sa.Column('fpi_ci_lower', sa.Float(), nullable=False),
    sa.Column('fpi_ci_upper', sa.Float(), nullable=False),
    sa.Column('fpi_24h', sa.Float(), nullable=True),
    sa.Column('cell_count_total', sa.Integer(), nullable=True),
    sa.Column('cell_count_breached', sa.Integer(), nullable=True),
    sa.Column('breach_fraction', sa.Float(), nullable=True),
    sa.Column('tier', sa.Enum('NORMAL', 'WATCH', 'WARNING', 'EMERGENCY', 'MONITORING', name='alerttier'), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('is_suppressed', sa.Boolean(), nullable=True),
    sa.Column('consecutive_cycles', sa.Integer(), nullable=True),
    sa.Column('dominant_signals', sa.JSON(), nullable=True),
    sa.Column('rainfall_3d_mm', sa.Float(), nullable=True),
    sa.Column('soil_moisture_percentile', sa.Float(), nullable=True),
    sa.Column('validated', sa.Boolean(), nullable=True),
    sa.Column('validated_at', sa.DateTime(), nullable=True),
    sa.Column('validation_source', sa.String(length=128), nullable=True),
    sa.Column('validation_notes', sa.Text(), nullable=True),
    sa.Column('issued_at', sa.DateTime(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=True),
    sa.Column('cleared_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_alerts_active_tier', 'alerts', ['is_active', 'tier'], unique=False)
    op.create_index(op.f('ix_alerts_alert_code'), 'alerts', ['alert_code'], unique=True)
    op.create_index('ix_alerts_district_active', 'alerts', ['district_code', 'is_active'], unique=False)
    op.create_index(op.f('ix_alerts_district_code'), 'alerts', ['district_code'], unique=False)
    op.create_index(op.f('ix_alerts_is_active'), 'alerts', ['is_active'], unique=False)
    op.create_index(op.f('ix_alerts_issued_at'), 'alerts', ['issued_at'], unique=False)
    op.create_index(op.f('ix_alerts_state_code'), 'alerts', ['state_code'], unique=False)
    op.create_index(op.f('ix_alerts_tier'), 'alerts', ['tier'], unique=False)
    op.create_table('districts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('state_code', sa.String(length=8), nullable=False),
    sa.Column('state_name', sa.String(length=64), nullable=False),
    sa.Column('district_code', sa.String(length=16), nullable=False),
    sa.Column('district_name', sa.String(length=64), nullable=False),
    sa.Column('block_code', sa.String(length=24), nullable=True),
    sa.Column('block_name', sa.String(length=64), nullable=True),
    sa.Column('geom', geoalchemy2.types.Geometry(geometry_type='MULTIPOLYGON', srid=4326, from_text='ST_GeomFromEWKT', name='geometry'), nullable=True),
    sa.Column('lat', sa.Float(), nullable=True),
    sa.Column('lon', sa.Float(), nullable=True),
    sa.Column('is_high_risk', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # op.create_index(idx_districts_geom...)
    op.create_index(op.f('ix_districts_block_code'), 'districts', ['block_code'], unique=False)
    op.create_index(op.f('ix_districts_district_code'), 'districts', ['district_code'], unique=True)
    op.create_index(op.f('ix_districts_state_code'), 'districts', ['state_code'], unique=False)
    op.create_index('ix_districts_state_district', 'districts', ['state_code', 'district_code'], unique=False)
    op.create_table('fpi_grid',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('cell_id', sa.String(length=32), nullable=False),
    sa.Column('lat', sa.Float(), nullable=False),
    sa.Column('lon', sa.Float(), nullable=False),
    sa.Column('geom', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326, from_text='ST_GeomFromEWKT', name='geometry', nullable=False), nullable=False),
    sa.Column('state_code', sa.String(length=8), nullable=True),
    sa.Column('district_code', sa.String(length=16), nullable=True),
    sa.Column('block_code', sa.String(length=24), nullable=True),
    sa.Column('fpi_score', sa.Float(), nullable=False),
    sa.Column('fpi_ci_lower', sa.Float(), nullable=False),
    sa.Column('fpi_ci_upper', sa.Float(), nullable=False),
    sa.Column('fpi_24h', sa.Float(), nullable=True),
    sa.Column('fpi_48h', sa.Float(), nullable=True),
    sa.Column('alert_tier', sa.Enum('NORMAL', 'WATCH', 'WARNING', 'EMERGENCY', 'MONITORING', name='alerttier'), nullable=True),
    sa.Column('rainfall_3d_mm', sa.Float(), nullable=True),
    sa.Column('rainfall_24h_forecast_mm', sa.Float(), nullable=True),
    sa.Column('soil_moisture_percentile', sa.Float(), nullable=True),
    sa.Column('slope_degrees', sa.Float(), nullable=True),
    sa.Column('ndvi_delta', sa.Float(), nullable=True),
    sa.Column('susceptibility_class', sa.Integer(), nullable=True),
    sa.Column('lithology_class', sa.String(length=32), nullable=True),
    sa.Column('dominant_signal', sa.String(length=64), nullable=True),
    sa.Column('model_version', sa.String(length=16), nullable=True),
    sa.Column('run_timestamp', sa.DateTime(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # Spatial indexes are automatically created by geoalchemy2
    # # spatial index
    op.create_index(op.f('ix_fpi_grid_block_code'), 'fpi_grid', ['block_code'], unique=False)
    op.create_index(op.f('ix_fpi_grid_cell_id'), 'fpi_grid', ['cell_id'], unique=True)
    op.create_index('ix_fpi_grid_district', 'fpi_grid', ['district_code', 'run_timestamp'], unique=False)
    op.create_index(op.f('ix_fpi_grid_district_code'), 'fpi_grid', ['district_code'], unique=False)
    op.create_index('ix_fpi_grid_location', 'fpi_grid', ['lat', 'lon'], unique=False)
    op.create_index(op.f('ix_fpi_grid_run_timestamp'), 'fpi_grid', ['run_timestamp'], unique=False)
    op.create_index('ix_fpi_grid_score', 'fpi_grid', ['fpi_score'], unique=False)
    op.create_index(op.f('ix_fpi_grid_state_code'), 'fpi_grid', ['state_code'], unique=False)
    op.create_table('fpi_history',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('cell_id', sa.String(length=32), nullable=False),
    sa.Column('run_timestamp', sa.DateTime(), nullable=False),
    sa.Column('lat', sa.Float(), nullable=False),
    sa.Column('lon', sa.Float(), nullable=False),
    sa.Column('district_code', sa.String(length=16), nullable=True),
    sa.Column('block_code', sa.String(length=24), nullable=True),
    sa.Column('fpi_score', sa.Float(), nullable=False),
    sa.Column('fpi_ci_lower', sa.Float(), nullable=False),
    sa.Column('fpi_ci_upper', sa.Float(), nullable=False),
    sa.Column('fpi_24h', sa.Float(), nullable=True),
    sa.Column('fpi_48h', sa.Float(), nullable=True),
    sa.Column('alert_tier', sa.Enum('NORMAL', 'WATCH', 'WARNING', 'EMERGENCY', 'MONITORING', name='alerttier'), nullable=True),
    sa.Column('rainfall_3d_mm', sa.Float(), nullable=True),
    sa.Column('soil_moisture_percentile', sa.Float(), nullable=True),
    sa.Column('slope_degrees', sa.Float(), nullable=True),
    sa.Column('dominant_signal', sa.String(length=64), nullable=True),
    sa.Column('model_version', sa.String(length=16), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_fpi_history_cell_id'), 'fpi_history', ['cell_id'], unique=False)
    op.create_index('ix_fpi_history_cell_time', 'fpi_history', ['cell_id', 'run_timestamp'], unique=False)
    op.create_index(op.f('ix_fpi_history_district_code'), 'fpi_history', ['district_code'], unique=False)
    op.create_index('ix_fpi_history_district_time', 'fpi_history', ['district_code', 'run_timestamp'], unique=False)
    op.create_index(op.f('ix_fpi_history_run_timestamp'), 'fpi_history', ['run_timestamp'], unique=False)
    op.create_table('landslide_events',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('event_name', sa.String(length=128), nullable=False),
    sa.Column('source', sa.String(length=64), nullable=False),
    sa.Column('source_id', sa.String(length=64), nullable=True),
    sa.Column('lat', sa.Float(), nullable=False),
    sa.Column('lon', sa.Float(), nullable=False),
    sa.Column('geom', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326, from_text='ST_GeomFromEWKT', name='geometry', nullable=False), nullable=False),
    sa.Column('district_code', sa.String(length=16), nullable=True),
    sa.Column('block_code', sa.String(length=24), nullable=True),
    sa.Column('location_description', sa.Text(), nullable=True),
    sa.Column('event_date', sa.DateTime(), nullable=False),
    sa.Column('deaths', sa.Integer(), nullable=True),
    sa.Column('injuries', sa.Integer(), nullable=True),
    sa.Column('displacement', sa.Integer(), nullable=True),
    sa.Column('economic_damage_cr', sa.Float(), nullable=True),
    sa.Column('trigger', sa.String(length=64), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('was_flagged_24h', sa.Boolean(), nullable=True),
    sa.Column('was_flagged_48h', sa.Boolean(), nullable=True),
    sa.Column('fpi_at_t24', sa.Float(), nullable=True),
    sa.Column('fpi_at_t12', sa.Float(), nullable=True),
    sa.Column('fpi_at_t6', sa.Float(), nullable=True),
    sa.Column('validation_notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # spatial index
    op.create_index('ix_events_date_district', 'landslide_events', ['event_date', 'district_code'], unique=False)
    op.create_index(op.f('ix_landslide_events_district_code'), 'landslide_events', ['district_code'], unique=False)
    op.create_index(op.f('ix_landslide_events_event_date'), 'landslide_events', ['event_date'], unique=False)
    op.create_table('alert_deliveries',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('alert_id', sa.UUID(), nullable=False),
    sa.Column('contact_id', sa.UUID(), nullable=True),
    sa.Column('channel', sa.Enum('WHATSAPP', 'EMAIL', 'SMS', 'CAP_FEED', name='deliverychannel'), nullable=False),
    sa.Column('recipient', sa.String(length=256), nullable=False),
    sa.Column('language', sa.String(length=8), nullable=True),
    sa.Column('message_body', sa.Text(), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'SENT', 'DELIVERED', 'FAILED', 'READ', name='deliverystatus'), nullable=True),
    sa.Column('external_message_id', sa.String(length=128), nullable=True),
    sa.Column('error_detail', sa.Text(), nullable=True),
    sa.Column('sent_at', sa.DateTime(), nullable=True),
    sa.Column('delivered_at', sa.DateTime(), nullable=True),
    sa.Column('read_at', sa.DateTime(), nullable=True),
    sa.Column('feedback_received', sa.Boolean(), nullable=True),
    sa.Column('feedback_at', sa.DateTime(), nullable=True),
    sa.Column('feedback_text', sa.String(length=256), nullable=True),
    sa.ForeignKeyConstraint(['alert_id'], ['alerts.id'], ),
    sa.ForeignKeyConstraint(['contact_id'], ['alert_contacts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alert_deliveries_alert_id'), 'alert_deliveries', ['alert_id'], unique=False)
    op.create_index(op.f('ix_alert_deliveries_status'), 'alert_deliveries', ['status'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    op.drop_index(op.f('ix_alert_deliveries_status'), table_name='alert_deliveries')
    op.drop_index(op.f('ix_alert_deliveries_alert_id'), table_name='alert_deliveries')
    op.drop_table('alert_deliveries')
    op.drop_index(op.f('ix_landslide_events_event_date'), table_name='landslide_events')
    op.drop_index(op.f('ix_landslide_events_district_code'), table_name='landslide_events')
    op.drop_index('ix_events_date_district', table_name='landslide_events')
    op.drop_index('idx_landslide_events_geom', table_name='landslide_events', postgresql_using='gist')
    op.drop_table('landslide_events')
    op.drop_index(op.f('ix_fpi_history_run_timestamp'), table_name='fpi_history')
    op.drop_index('ix_fpi_history_district_time', table_name='fpi_history')
    op.drop_index(op.f('ix_fpi_history_district_code'), table_name='fpi_history')
    op.drop_index('ix_fpi_history_cell_time', table_name='fpi_history')
    op.drop_index(op.f('ix_fpi_history_cell_id'), table_name='fpi_history')
    op.drop_table('fpi_history')
    op.drop_index(op.f('ix_fpi_grid_state_code'), table_name='fpi_grid')
    op.drop_index('ix_fpi_grid_score', table_name='fpi_grid')
    op.drop_index(op.f('ix_fpi_grid_run_timestamp'), table_name='fpi_grid')
    op.drop_index('ix_fpi_grid_location', table_name='fpi_grid')
    op.drop_index(op.f('ix_fpi_grid_district_code'), table_name='fpi_grid')
    op.drop_index('ix_fpi_grid_district', table_name='fpi_grid')
    op.drop_index(op.f('ix_fpi_grid_cell_id'), table_name='fpi_grid')
    op.drop_index(op.f('ix_fpi_grid_block_code'), table_name='fpi_grid')
    op.drop_index('idx_fpi_grid_geom', table_name='fpi_grid', postgresql_using='gist')
    op.drop_table('fpi_grid')
    op.drop_index('ix_districts_state_district', table_name='districts')
    op.drop_index(op.f('ix_districts_state_code'), table_name='districts')
    op.drop_index(op.f('ix_districts_district_code'), table_name='districts')
    op.drop_index(op.f('ix_districts_block_code'), table_name='districts')
    op.drop_index('idx_districts_geom', table_name='districts', postgresql_using='gist')
    op.drop_table('districts')
    op.drop_index(op.f('ix_alerts_tier'), table_name='alerts')
    op.drop_index(op.f('ix_alerts_state_code'), table_name='alerts')
    op.drop_index(op.f('ix_alerts_issued_at'), table_name='alerts')
    op.drop_index(op.f('ix_alerts_is_active'), table_name='alerts')
    op.drop_index(op.f('ix_alerts_district_code'), table_name='alerts')
    op.drop_index('ix_alerts_district_active', table_name='alerts')
    op.drop_index(op.f('ix_alerts_alert_code'), table_name='alerts')
    op.drop_index('ix_alerts_active_tier', table_name='alerts')
    op.drop_table('alerts')
    op.drop_index('ix_contacts_district', table_name='alert_contacts')
    op.drop_index(op.f('ix_alert_contacts_state_code'), table_name='alert_contacts')
    op.drop_index(op.f('ix_alert_contacts_district_code'), table_name='alert_contacts')
    op.drop_table('alert_contacts')
    # ### end Alembic commands ###
