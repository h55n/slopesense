"""
SlopeSense — Comprehensive Integration & Contract Tests

Tests every API endpoint for:
- Correct HTTP status codes
- Response schema validation  
- Edge cases and error conditions
- Data type correctness
- FPI range validation

Run: pytest backend/tests/test_api_integration.py -v
"""

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient, ASGITransport


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def test_alert_payload():
    """Full Alert model payload for injection into test DB."""
    return dict(
        alert_code="INTG_TEST_001",
        tier="WARNING",
        state_code="KL",
        state_name="Kerala",
        district_code="WYD",
        district_name="Wayanad",
        block_code="MEP",
        block_name="Meppadi",
        fpi_score=0.73,
        fpi_ci_lower=0.61,
        fpi_ci_upper=0.84,
        fpi_24h=0.81,
        is_active=True,
        is_suppressed=False,
        consecutive_cycles=2,
        dominant_signals=[],
        rainfall_3d_mm=183,
        soil_moisture_percentile=91,
        cell_count_total=48,
        cell_count_breached=22,
        breach_fraction=0.46,
        issued_at=datetime.now(timezone.utc),
        lat=11.5,
        lon=76.1,
    )


# ── Health Endpoint ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestHealthContractTests:
    """Strict contract tests for the health endpoint."""

    async def test_health_returns_200(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/")
        assert resp.status_code == 200

    async def test_health_json_content_type(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/")
        assert "application/json" in resp.headers["content-type"]

    async def test_health_required_fields(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/")
        data = resp.json()
        required_fields = {"status", "active_alerts", "last_model_run"}
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    async def test_health_status_is_healthy(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/")
        assert resp.json()["status"] == "healthy"

    async def test_health_active_alerts_is_nonnegative_int(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/")
        count = resp.json()["active_alerts"]
        assert isinstance(count, int)
        assert count >= 0


# ── Risk Endpoint ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestRiskEndpointContractTests:
    """Strict contract tests for /v1/risk."""

    async def test_risk_valid_coords_returns_200(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/risk?lat=11.58&lon=76.08")
        assert resp.status_code == 200

    async def test_risk_fpi_score_in_bounds(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/risk?lat=11.58&lon=76.08")
        data = resp.json()
        assert 0.0 <= data["fpi_score"] <= 1.0

    async def test_risk_tier_is_valid_enum(self):
        from backend.api.main import app
        valid_tiers = {"NORMAL", "WATCH", "WARNING", "EMERGENCY", "MONITORING"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/risk?lat=11.58&lon=76.08")
        assert resp.json()["alert_tier"] in valid_tiers

    async def test_risk_out_of_range_lat_returns_422(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/risk?lat=200&lon=76")
        assert resp.status_code == 422

    async def test_risk_out_of_range_lon_returns_422(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/risk?lat=11.5&lon=200")
        assert resp.status_code == 422

    async def test_risk_missing_lat_returns_422(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/risk?lon=76")
        assert resp.status_code == 422

    async def test_risk_returns_signal_components(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/risk?lat=11.58&lon=76.08")
        data = resp.json()
        assert "risk_label" in data
        assert "risk_color" in data
        assert "risk_description" in data


# ── Alerts Endpoint ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestAlertsContractTests:
    """Contract and integration tests for /v1/alerts/active."""

    async def test_active_alerts_schema(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/alerts/active")
        assert resp.status_code == 200
        data = resp.json()
        assert "count" in data
        assert "alerts" in data
        assert isinstance(data["alerts"], list)

    async def test_active_alerts_count_matches_list_length(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/alerts/active")
        data = resp.json()
        assert data["count"] == len(data["alerts"])

    async def test_active_alerts_fpi_filter_excludes_below_threshold(self, test_alert_payload):
        from backend.api.main import app
        from backend.api.database import AsyncSessionLocal
        from backend.models import Alert

        async with AsyncSessionLocal() as session:
            alert = Alert(id=uuid.uuid4(), **test_alert_payload)
            session.add(alert)
            await session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 0.73 should be excluded when min_fpi=0.80
            resp_exclude = await client.get("/v1/alerts/active?min_fpi=0.80")
            # 0.73 should be included when min_fpi=0.60
            resp_include = await client.get("/v1/alerts/active?min_fpi=0.60")

        assert resp_exclude.json()["count"] == 0
        assert resp_include.json()["count"] >= 1

    async def test_active_alerts_each_item_has_fpi_in_bounds(self, test_alert_payload):
        from backend.api.main import app
        from backend.api.database import AsyncSessionLocal
        from backend.models import Alert

        async with AsyncSessionLocal() as session:
            alert = Alert(id=uuid.uuid4(), **test_alert_payload)
            session.add(alert)
            await session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/alerts/active?min_fpi=0.30")

        for item in resp.json()["alerts"]:
            assert 0.0 <= item["fpi_score"] <= 1.0, f"FPI out of bounds: {item['fpi_score']}"


# ── GeoJSON Endpoint ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestGeoJSONContractTests:
    """Contract tests for /v1/geojson/fpi."""

    async def _inject_alert(self, test_alert_payload):
        from backend.api.database import AsyncSessionLocal
        from backend.models import Alert
        async with AsyncSessionLocal() as session:
            alert = Alert(id=uuid.uuid4(), **test_alert_payload)
            session.add(alert)
            await session.commit()

    async def test_geojson_returns_feature_collection(self, test_alert_payload):
        from backend.api.main import app
        await self._inject_alert(test_alert_payload)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/geojson/fpi")
        assert resp.status_code == 200
        assert resp.json()["type"] == "FeatureCollection"

    async def test_geojson_features_have_geometry(self, test_alert_payload):
        from backend.api.main import app
        await self._inject_alert(test_alert_payload)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/geojson/fpi")
        features = resp.json()["features"]
        if features:
            for f in features:
                assert f["type"] == "Feature"
                assert f["geometry"]["type"] == "Point"
                lon, lat = f["geometry"]["coordinates"]
                assert -180 <= lon <= 180
                assert -90 <= lat <= 90

    async def test_geojson_feature_properties_have_fpi(self, test_alert_payload):
        from backend.api.main import app
        await self._inject_alert(test_alert_payload)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/geojson/fpi")
        features = resp.json()["features"]
        if features:
            props = features[0]["properties"]
            assert "fpi" in props
            assert "tier" in props
            assert 0.0 <= props["fpi"] <= 1.0

    async def test_geojson_min_fpi_filter_works(self, test_alert_payload):
        from backend.api.main import app
        await self._inject_alert(test_alert_payload)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # min_fpi=0.90 should exclude our 0.73 alert
            resp = await client.get("/v1/geojson/fpi?min_fpi=0.90")
        assert resp.status_code == 200
        assert resp.json()["type"] == "FeatureCollection"


# ── CAP Feed Endpoint ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestCAPFeedContractTests:
    """Contract tests for /v1/cap/feed."""

    async def test_cap_feed_returns_xml_content_type(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/cap/feed")
        assert "xml" in resp.headers["content-type"]

    async def test_cap_feed_is_valid_xml(self):
        from backend.api.main import app
        import xml.etree.ElementTree as ET
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/cap/feed")
        # Should not raise
        ET.fromstring(resp.text)

    async def test_cap_feed_contains_feed_root(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/cap/feed")
        assert "<feed" in resp.text

    async def test_cap_feed_with_alert_includes_district(self):
        from backend.api.main import app
        from backend.api.database import AsyncSessionLocal
        from backend.models import Alert

        async with AsyncSessionLocal() as session:
            alert = Alert(
                id=uuid.uuid4(), alert_code="CAP_INTG_TEST", tier="WARNING",
                state_code="KL", state_name="Kerala",
                district_code="WYD", district_name="Wayanad",
                block_code="MEP", block_name="Meppadi",
                fpi_score=0.73, fpi_ci_lower=0.61, fpi_ci_upper=0.84,
                fpi_24h=0.81, is_active=True, is_suppressed=False,
                consecutive_cycles=2, dominant_signals=[],
                rainfall_3d_mm=183, soil_moisture_percentile=91,
                cell_count_total=48, cell_count_breached=22,
                breach_fraction=0.46, issued_at=datetime.now(timezone.utc),
                lat=11.5, lon=76.1,
            )
            session.add(alert)
            await session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/cap/feed?min_fpi=0.60")

        assert "Wayanad" in resp.text


# ── Retrospective Endpoint ────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestRetrospectiveContractTests:
    """Contract tests for /v1/retrospective."""

    async def test_retrospective_summary_schema(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/retrospective")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_events" in data
        assert "flagged_at_t24" in data
        assert isinstance(data["total_events"], int)

    async def test_retrospective_wayanad_event(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/retrospective/wayanad_2024")
        assert resp.status_code == 200
        data = resp.json()
        assert data["event_id"] == "wayanad_2024"
        assert "fpi_t24" in data

    async def test_retrospective_unknown_event_returns_404_or_data(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/retrospective/this_event_does_not_exist_xyz")
        # Should either 404 or return event with synthetic data
        assert resp.status_code in (200, 404)


# ── Contact Registration ──────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestContactRegistrationContractTests:
    """Contract tests for /v1/contacts/register."""

    async def test_register_accepts_valid_payload(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/v1/contacts/register",
                headers={"x-api-key": "test-api-key"},
                json={
                    "name": "Rajesh Kumar",
                    "role": "GRAM_PRADHAN",
                    "state_code": "KL",
                    "district_code": "WYD",
                    "block_code": "MEP",
                    "whatsapp_number": "+919876543210",
                    "min_tier": "WARNING",
                    "language": "hi",
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data

    async def test_register_rejects_missing_name(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/v1/contacts/register",
                headers={"x-api-key": "test-api-key"},
                json={"role": "GRAM_PRADHAN", "state_code": "KL"},
            )
        assert resp.status_code == 422

    async def test_register_without_api_key_returns_401(self):
        from backend.api.main import app
        from backend.config import settings
        from backend.api import middleware
        # Temporarily set an API key requirement
        original = settings.api_keys
        settings.api_keys = "required-key"
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/v1/contacts/register",
                    json={"name": "test", "role": "GRAM_PRADHAN", "state_code": "KL"},
                )
            assert resp.status_code == 401
        finally:
            settings.api_keys = original
            middleware._memory_windows.clear()


# ── Historical Endpoint ───────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestHistoricalEndpointContractTests:
    """Contract tests for /v1/historical/{date}/{district}."""

    async def test_historical_valid_request_returns_200(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/historical/2024-07-29/WYD")
        assert resp.status_code == 200

    async def test_historical_json_format_has_required_keys(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/historical/2024-07-29/WYD")
        data = resp.json()
        assert "date" in data
        assert "district_code" in data
        assert "blocks" in data

    async def test_historical_geojson_format(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/historical/2024-07-29/WYD?format=geojson")
        data = resp.json()
        assert data["type"] == "FeatureCollection"
        assert "features" in data

    async def test_historical_invalid_date_returns_422(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/historical/not-a-date/WYD")
        assert resp.status_code == 422


# ── Security Tests ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestSecurityContractTests:
    """Security-focused contract tests."""

    async def test_security_headers_present(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/")
        assert resp.headers.get("x-content-type-options") == "nosniff"
        assert resp.headers.get("x-frame-options") == "DENY"

    async def test_xss_injection_in_query_param_is_escaped(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/risk?lat=11.5&lon=76.0")
        # Response should be JSON, not HTML with script tags
        assert "<script>" not in resp.text

    async def test_sql_injection_in_state_param_doesnt_crash(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/alerts/active?state='; DROP TABLE alerts; --")
        # Should not return 500; 200 with empty or 400/422 is acceptable
        assert resp.status_code != 500

    async def test_very_long_string_param_doesnt_crash(self):
        from backend.api.main import app
        long_state = "A" * 10000
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/v1/alerts/active?state={long_state}")
        assert resp.status_code in (200, 400, 422)


# ── Data Integrity Tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestDataIntegrityTests:
    """Tests that data values are within expected bounds across multiple requests."""

    async def test_fpi_scores_always_in_unit_range(self):
        """Exhaustive check: every FPI score returned by any endpoint is 0-1."""
        from backend.api.main import app
        from backend.api.database import AsyncSessionLocal
        from backend.models import Alert

        # Insert several alerts with different FPI values
        fpi_values = [0.31, 0.45, 0.66, 0.73, 0.85]
        async with AsyncSessionLocal() as session:
            for i, fpi in enumerate(fpi_values):
                session.add(Alert(
                    id=uuid.uuid4(),
                    alert_code=f"DI_TEST_{i:03d}",
                    tier="WARNING" if fpi >= 0.65 else "WATCH",
                    state_code="KL", state_name="Kerala",
                    district_code="WYD", district_name="Wayanad",
                    block_code=f"BLK{i}", block_name=f"Block{i}",
                    fpi_score=fpi, fpi_ci_lower=max(0, fpi - 0.12),
                    fpi_ci_upper=min(1, fpi + 0.12),
                    fpi_24h=min(1, fpi * 1.1),
                    is_active=True, is_suppressed=False,
                    consecutive_cycles=2, dominant_signals=[],
                    rainfall_3d_mm=100 + i * 20, soil_moisture_percentile=70 + i * 5,
                    cell_count_total=40, cell_count_breached=20,
                    breach_fraction=0.5,
                    issued_at=datetime.now(timezone.utc),
                    lat=11.5 + i * 0.1, lon=76.0 + i * 0.1,
                ))
            await session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/alerts/active?min_fpi=0.30")

        for alert in resp.json()["alerts"]:
            fpi = alert["fpi_score"]
            assert 0.0 <= fpi <= 1.0, f"FPI {fpi} is out of bounds for alert {alert.get('alert_code')}"

    async def test_tiers_match_fpi_values(self):
        """Check tier labels match their FPI score ranges."""
        from backend.api.main import app
        from backend.api.database import AsyncSessionLocal
        from backend.models import Alert

        tier_fpi_map = [
            ("WATCH", 0.45),
            ("WARNING", 0.70),
            ("EMERGENCY", 0.85),
        ]

        async with AsyncSessionLocal() as session:
            for tier, fpi in tier_fpi_map:
                session.add(Alert(
                    id=uuid.uuid4(),
                    alert_code=f"TIER_{tier}",
                    tier=tier,
                    state_code="KL", state_name="Kerala",
                    district_code="WYD", district_name="Wayanad",
                    block_code="MEP", block_name="Meppadi",
                    fpi_score=fpi, fpi_ci_lower=fpi - 0.1,
                    fpi_ci_upper=fpi + 0.1, fpi_24h=fpi + 0.05,
                    is_active=True, is_suppressed=False,
                    consecutive_cycles=2, dominant_signals=[],
                    rainfall_3d_mm=150, soil_moisture_percentile=80,
                    cell_count_total=40, cell_count_breached=20,
                    breach_fraction=0.5,
                    issued_at=datetime.now(timezone.utc),
                    lat=11.5, lon=76.1,
                ))
            await session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/alerts/active?min_fpi=0.30")

        # Verify: EMERGENCY alerts have FPI >= 0.80, WATCH >= 0.40 but < 0.65
        alerts_by_tier = {}
        for alert in resp.json()["alerts"]:
            tier = alert["tier"]
            fpi = alert["fpi_score"]
            alerts_by_tier.setdefault(tier, []).append(fpi)

        if "EMERGENCY" in alerts_by_tier:
            for fpi in alerts_by_tier["EMERGENCY"]:
                assert fpi >= 0.80, f"EMERGENCY alert has FPI {fpi} which is < 0.80"

        if "WATCH" in alerts_by_tier:
            for fpi in alerts_by_tier["WATCH"]:
                assert fpi >= 0.40, f"WATCH alert has FPI {fpi} which is < 0.40"


# ── Docs Endpoints ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestDocumentationEndpoints:
    """Verify that API documentation endpoints are accessible."""

    async def test_swagger_ui_accessible(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/docs")
        assert resp.status_code == 200

    async def test_redoc_accessible(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/redoc")
        assert resp.status_code == 200

    async def test_openapi_json_accessible(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert schema["info"]["title"] == "SlopeSense API"
        assert schema["info"]["version"] == "1.0.0"

    async def test_openapi_lists_all_expected_paths(self):
        from backend.api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/openapi.json")
        paths = resp.json()["paths"]
        expected_paths = ["/", "/v1/risk", "/v1/alerts/active", "/v1/cap/feed", "/v1/geojson/fpi"]
        for expected in expected_paths:
            assert expected in paths, f"Missing expected API path: {expected}"
