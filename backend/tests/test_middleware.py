"""Tests for API middleware."""

import logging

import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_security_headers_present():
    from backend.api.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/")

    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"


@pytest.mark.asyncio
async def test_request_logging_contains_request_id(caplog):
    from backend.api.main import app

    caplog.set_level(logging.INFO, logger="slopesense.api")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/", headers={"x-request-id": "test-request-id"})

    assert "test-request-id" in caplog.text


@pytest.mark.asyncio
async def test_api_key_rejects_when_configured(monkeypatch):
    from backend.api import middleware
    from backend.api.main import app
    from backend.config import settings

    monkeypatch.setattr(settings, "api_keys", "valid-key")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/v1/contacts/register",
            json={
                "name": "Officer",
                "role": "district_collector",
                "whatsapp_number": "+919876543210",
                "state_code": "KL",
            },
        )

    assert resp.status_code == 401
    monkeypatch.setattr(settings, "api_keys", "")
    middleware._memory_windows.clear()
