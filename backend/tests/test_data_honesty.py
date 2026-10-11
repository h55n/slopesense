"""Regression checks for fail-closed safety and durable API keys."""

import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_generated_key_authenticates_and_is_hashed():
    from backend.api.main import app
    from backend.api.database import AsyncSessionLocal
    from backend.models import ApiKey
    from backend.api.apikeys import key_digest
    from sqlalchemy import select

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        r = await c.post(
            "/v1/apikeys/generate", json={"name": "QA", "email": "qa@example.org"}
        )
        assert r.status_code == 200
        key = r.json()["key"]
        async with AsyncSessionLocal() as db:
            row = (
                (
                    await db.execute(
                        select(ApiKey).where(ApiKey.email == "qa@example.org")
                    )
                )
                .scalars()
                .one()
            )
            assert row.key == key_digest(key)
            assert row.key != key
        assert (
            await c.get("/v1/districts/KL", headers={"x-api-key": key})
        ).status_code == 200
        assert (
            await c.get("/v1/districts/KL", headers={"x-api-key": "invalid"})
        ).status_code == 401
        assert (
            await c.post(
                "/v1/apikeys/generate", json={"name": "QA", "email": "qa@example.org"}
            )
        ).status_code == 400


@pytest.mark.asyncio
async def test_sample_cap_cannot_be_actual():
    from backend.api.main import app
    import xml.etree.ElementTree as ET

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        r = await c.get("/v1/cap/feed?min_fpi=0")
        assert r.status_code == 200
        root = ET.fromstring(r.text)
        for status in root.iter("{urn:oasis:names:tc:emergency:cap:1.2}status"):
            assert status.text == "Test"
        assert "<certainty>Observed" not in r.text


@pytest.mark.asyncio
async def test_registry_failure_never_reports_success():
    from backend.api.main import app
    from backend.api.database import get_db

    async def unavailable():
        yield None

    app.dependency_overrides[get_db] = unavailable
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            r = await c.post(
                "/v1/contacts/register",
                headers={"x-api-key": "test-api-key"},
                json={
                    "name": "QA",
                    "role": "researcher",
                    "state_code": "KL",
                    "whatsapp_number": "+910000000000",
                },
            )
            assert r.status_code == 503
            assert (
                await c.post(
                    "/v1/apikeys/generate",
                    json={"name": "QA", "email": "qa@example.org"},
                )
            ).status_code == 503
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_credentials_cannot_activate_whatsapp(monkeypatch):
    from backend.alert.dispatcher import WhatsAppDispatcher, EmailDispatcher
    from datetime import datetime, timezone

    monkeypatch.setenv("SMTP_USER", "test@example.org")
    monkeypatch.setenv("WHATSAPP_API_TOKEN", "fake-test-not-a-secret")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "fake-id")

    def forbidden(*a, **k):
        raise AssertionError("No network send is allowed")

    monkeypatch.setattr("aiohttp.ClientSession", forbidden)
    monkeypatch.setattr("smtplib.SMTP", forbidden)
    result = await WhatsAppDispatcher().send_text_message("+910000000000", "TEST")
    assert result["status"] == "disabled"
    assert result["message_id"] is None
    assert (
        await EmailDispatcher().send_daily_digest(
            ["test@example.org"], [], datetime.now(timezone.utc)
        )
        is False
    )
