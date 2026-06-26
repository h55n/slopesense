"""Tests for WhatsApp webhook handling."""

import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_whatsapp_webhook_verification_accepts_valid_token():
    from backend.api.main import app
    from backend.config import settings

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/v1/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "abc123",
                "hub.verify_token": settings.whatsapp_verify_token,
            },
        )

    assert resp.status_code == 200
    assert resp.text == "abc123"


@pytest.mark.asyncio
async def test_whatsapp_webhook_verification_rejects_bad_token():
    from backend.api.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/v1/webhooks/whatsapp",
            params={"hub.mode": "subscribe", "hub.challenge": "abc123", "hub.verify_token": "bad"},
        )

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_no_event_feedback_processed():
    from backend.api.main import app

    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {"id": "wamid.1", "from": "919876543210", "text": {"body": "NO EVENT"}}
                            ]
                        }
                    }
                ]
            }
        ]
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/v1/webhooks/whatsapp", json=payload)

    assert resp.status_code == 200
    assert resp.json()["events_processed"] == 1
