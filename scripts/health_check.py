"""Comprehensive SlopeSense deployment health check."""

import asyncio
import sys

import httpx

CHECKS = [
    ("API health", "GET", "http://localhost:8000/", None),
    ("Active alerts", "GET", "http://localhost:8000/v1/alerts/active", None),
    ("GeoJSON FPI", "GET", "http://localhost:8000/v1/geojson/fpi", None),
    ("Retrospective", "GET", "http://localhost:8000/v1/retrospective", None),
    ("CAP feed", "GET", "http://localhost:8000/v1/cap/feed", None),
    ("Dashboard", "GET", "http://localhost:3000/", None),
]


async def run_checks():
    failed = 0
    async with httpx.AsyncClient(timeout=10) as client:
        for name, method, url, body in CHECKS:
            try:
                resp = await client.request(method, url, json=body)
                marker = "OK" if resp.status_code < 400 else "FAIL"
                if resp.status_code >= 400:
                    failed += 1
                print(f"{marker} {name}: HTTP {resp.status_code} ({len(resp.content)} bytes)")
            except Exception as exc:
                print(f"FAIL {name}: {exc}")
                failed += 1
    return failed


if __name__ == "__main__":
    failed_count = asyncio.run(run_checks())
    print("\nALL CHECKS PASSED" if failed_count == 0 else f"\n{failed_count} CHECKS FAILED")
    sys.exit(0 if failed_count == 0 else 1)
