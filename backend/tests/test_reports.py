"""Tests for PDF report generation."""

import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_pdf_generation_returns_pdf_bytes():
    from datetime import datetime, timezone

    from backend.api.reports import generate_district_report

    pdf = await generate_district_report("WYD", "Wayanad", [], datetime.now(timezone.utc))
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000


@pytest.mark.asyncio
async def test_pdf_endpoint_content_type():
    from backend.api.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/districts/WYD/report.pdf", headers={"x-api-key": "test-api-key"})

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")
