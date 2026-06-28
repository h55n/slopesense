"""
SlopeSense — FastAPI Integration Tests

Tests the REST API endpoints using httpx async client.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
class TestHealthEndpoint:
    async def test_health_returns_healthy(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data

    async def test_health_includes_alert_count(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/")
        data = resp.json()
        assert "active_alerts" in data
        assert isinstance(data["active_alerts"], int)


@pytest.mark.asyncio
class TestAlertsEndpoint:
    async def test_active_alerts_returns_list(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/alerts/active")
        assert resp.status_code == 200
        data = resp.json()
        assert "alerts" in data
        assert "count" in data
        assert isinstance(data["alerts"], list)

    async def test_active_alerts_min_fpi_filter(self):
        from backend.api.main import app
        from backend.api.database import AsyncSessionLocal
        from backend.models import Alert
        import uuid
        
        async with AsyncSessionLocal() as session:
            alert = Alert(
                id=uuid.uuid4(), alert_code="TEST", tier="WARNING",
                state_code="KL", state_name="Kerala",
                district_code="WYD", district_name="Wayanad",
                block_code="MEP", block_name="Meppadi",
                fpi_score=0.73, fpi_ci_lower=0.61, fpi_ci_upper=0.84,
                fpi_24h=0.81, is_active=True, is_suppressed=False,
                consecutive_cycles=2, dominant_signals=[],
                rainfall_3d_mm=183, soil_moisture_percentile=91,
                cell_count_total=48, cell_count_breached=22,
                breach_fraction=0.46,
                issued_at=datetime.now(timezone.utc),
                lat=11.5, lon=76.1
            )
            session.add(alert)
            await session.commit()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp_high = await client.get("/v1/alerts/active?min_fpi=0.80")
            resp_low = await client.get("/v1/alerts/active?min_fpi=0.60")
        assert resp_high.json()["count"] == 0  # 0.73 < 0.80
        assert resp_low.json()["count"] == 1   # 0.73 > 0.60


@pytest.mark.asyncio
class TestRiskEndpoint:
    async def test_risk_point_returns_fpi(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/risk?lat=11.58&lon=76.08")
        assert resp.status_code == 200
        data = resp.json()
        assert "fpi_score" in data
        assert 0.0 <= data["fpi_score"] <= 1.0
        assert "alert_tier" in data
        assert data["alert_tier"] in ("NORMAL", "WATCH", "WARNING", "EMERGENCY", "MONITORING")

    async def test_risk_point_invalid_coords(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/risk?lat=200&lon=76")
        assert resp.status_code == 422  # validation error


@pytest.mark.asyncio
class TestRetrospectiveEndpoint:
    async def test_retrospective_summary(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/retrospective")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_events" in data
        assert data["total_events"] == 6
        assert "flagged_at_t24" in data
        assert "passed" in data

    async def test_retrospective_wayanad(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/retrospective/wayanad_2024")
        assert resp.status_code == 200
        data = resp.json()
        assert data["event_id"] == "wayanad_2024"
        assert "fpi_t24" in data


@pytest.mark.asyncio
class TestHistoricalEndpoint:
    async def test_historical_json_structure(self):
        from backend.api.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/historical/2024-07-29/WYD")

        assert resp.status_code == 200
        data = resp.json()
        assert data["district_code"] == "WYD"
        assert "cells" in data
        assert "blocks" in data

    async def test_historical_geojson_structure(self):
        from backend.api.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/historical/2024-07-29/WYD?format=geojson")

        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "FeatureCollection"
        assert "features" in data


@pytest.mark.asyncio
class TestCAPFeed:
    async def test_cap_feed_xml_response(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/cap/feed")
        assert resp.status_code == 200
        assert "xml" in resp.headers["content-type"]
        assert "<?xml" in resp.text

    async def test_cap_feed_with_injected_alert(self):
        from backend.api.main import app
        from backend.api.database import AsyncSessionLocal
        from backend.models import Alert
        import uuid
        
        async with AsyncSessionLocal() as session:
            alert = Alert(
                id=uuid.uuid4(), alert_code="KL_CAP_TEST",
                tier="WARNING", state_code="KL", state_name="Kerala",
                district_code="WYD", district_name="Wayanad",
                block_code="MEP", block_name="Meppadi",
                fpi_score=0.73, fpi_ci_lower=0.61, fpi_ci_upper=0.84,
                fpi_24h=0.81, is_active=True, is_suppressed=False,
                consecutive_cycles=2, dominant_signals=[],
                rainfall_3d_mm=183, soil_moisture_percentile=91,
                cell_count_total=48, cell_count_breached=22,
                breach_fraction=0.46,
                issued_at=datetime.now(timezone.utc),
                lat=11.5, lon=76.1
            )
            session.add(alert)
            await session.commit()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/cap/feed?min_fpi=0.60")
        assert "Wayanad" in resp.text
        assert "WARNING" in resp.text

@pytest.mark.asyncio
class TestGeoJSONEndpoint:
    async def test_geojson_fpi_structure(self):
        from backend.api.main import app
        from backend.api.database import AsyncSessionLocal
        from backend.models import Alert
        import uuid
        
        async with AsyncSessionLocal() as session:
            alert = Alert(
                id=uuid.uuid4(), alert_code="GEO_TEST", tier="WARNING",
                state_code="KL", state_name="Kerala",
                district_code="WYD", district_name="Wayanad",
                block_code="MEP", block_name="Meppadi",
                fpi_score=0.73, fpi_ci_lower=0.61, fpi_ci_upper=0.84,
                fpi_24h=0.81, is_active=True, is_suppressed=False,
                consecutive_cycles=2, dominant_signals=[],
                rainfall_3d_mm=183, soil_moisture_percentile=91,
                cell_count_total=48, cell_count_breached=22,
                breach_fraction=0.46,
                issued_at=datetime.now(timezone.utc),
                lat=11.5, lon=76.1
            )
            session.add(alert)
            await session.commit()
            
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/geojson/fpi")
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "FeatureCollection"
        assert "features" in data
        assert isinstance(data["features"], list)
        # Should have synthetic Wayanad data
        assert len(data["features"]) > 0

    async def test_geojson_feature_properties(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/geojson/fpi")
        features = resp.json()["features"]
        if features:
            props = features[0]["properties"]
            assert "fpi" in props
            assert "tier" in props
            assert 0 <= props["fpi"] <= 1


@pytest.mark.asyncio
class TestContactRegistration:
    async def test_register_contact_success(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/v1/contacts/register",
                headers={"x-api-key": "test-api-key"},
                json={
                    "name": "Test SDMA Officer",
                    "role": "SDMA_OFFICIAL",
                    "state_code": "KL",
                    "whatsapp_number": "+919876543210",
                    "min_tier": "WARNING",
                    "language": "en"
                }
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "registered"
        assert "id" in data

    async def test_register_contact_missing_required_fields(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/v1/contacts/register",
                headers={"x-api-key": "test-api-key"},
                json={
                    "name": "Incomplete User"
                    # missing required: role, whatsapp_number, state_code
                }
            )
        assert resp.status_code == 422
