"""Public production health/safety checks. No writes, credentials or notifications."""

import json
import os
from pathlib import Path
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import xml.etree.ElementTree as ET

BASE = os.environ.get("SMOKE_BASE_URL", "https://slopesense-olive.vercel.app").rstrip(
    "/"
)


def inspect(path, status, body):
    if path.startswith("/api/v1/risk"):
        return status == 503 and "unavailable" in body.decode().lower()
    if path == "/api/v1/districts/KL":
        return status == 401
    if status != 200:
        return False
    if path == "/api/health":
        return json.loads(body).get("status") == "healthy"
    if path.startswith("/api/v1/cap/feed"):
        root = ET.fromstring(body)
        return all(
            x.text == "Test"
            for x in root.iter("{urn:oasis:names:tc:emergency:cap:1.2}status")
        )
    if path == "/api/v1/source-observations":
        data = json.loads(body)
        return (
            data.get("count") == 6
            and data.get("warning_publication_enabled") is False
            and all(
                not x.get("stale", True) and x.get("used_for_warnings") is False
                for x in data.get("observations", [])
            )
        )
    if path.endswith(".pdf"):
        return body.startswith(b"%PDF")
    return len(body) > 500 and b"<html" in body.lower()


def run():
    paths = [
        "/",
        "/districts",
        "/status",
        "/developers",
        "/register",
        "/api-docs",
        "/api/health",
        "/api/v1/cap/feed?min_fpi=0",
        "/api/v1/source-observations",
        "/api/v1/risk?lat=11.58&lon=76.08",
        "/api/v1/districts/KL",
        "/api/v1/districts/DAR/report.pdf",
    ]
    results = []
    for path in paths:
        start = time.monotonic()
        try:
            request = Request(
                BASE + path, headers={"x-api-key": "invalid-healthcheck-key"}
            )
            try:
                response = urlopen(request, timeout=30)
            except HTTPError as exc:
                response = exc
            body = response.read()
            passed = inspect(path, response.status, body)
            result = {"path": path, "http_status": response.status, "passed": passed}
        except Exception as exc:
            result = {"path": path, "passed": False, "error_type": type(exc).__name__}
        result["seconds"] = round(time.monotonic() - start, 2)
        results.append(result)
        print(("PASS" if result["passed"] else "FAIL"), path, result)
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "base_url": BASE,
        "passed": all(x["passed"] for x in results),
        "checks": results,
    }
    Path("smoke-results.json").write_text(json.dumps(report, indent=2))
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as f:
            f.write(
                "# Production smoke check\n\n"
                + "\n".join(
                    f"- {'PASS' if x['passed'] else 'FAIL'} `{x['path']}`"
                    for x in results
                )
            )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(run())
