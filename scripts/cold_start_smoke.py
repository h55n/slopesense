"""Import serverless entry point with no DB configuration and call health via ASGI.

Run in a fresh process with the deployed root requirements, not backend's richer
research environment. Never connects to a production database.
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.pop("DATABASE_URL", None)
os.environ["VERCEL"] = "1"
os.environ["ENVIRONMENT"] = "test"


async def check():
    # A serverless filesystem is writable only in /tmp. Import with a writable cwd
    # but no project data files in it, exercising packaged Python-only imports.
    with tempfile.TemporaryDirectory() as cwd:
        os.chdir(cwd)
        from api.index import app

        messages = []
        delivered = False

        async def receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": b"", "more_body": False}
            await asyncio.sleep(0.01)
            return {"type": "http.disconnect"}

        async def send(message):
            messages.append(message)

        await app(
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "GET",
                "scheme": "https",
                "path": "/api/health",
                "raw_path": b"/api/health",
                "query_string": b"",
                "root_path": "",
                "headers": [],
                "server": ("localhost", 443),
                "client": ("127.0.0.1", 1),
            },
            receive,
            send,
        )
        status = next(
            m["status"] for m in messages if m["type"] == "http.response.start"
        )
        body = b"".join(
            m.get("body", b"") for m in messages if m["type"] == "http.response.body"
        )
        assert status == 200, (status, body)
        assert json.loads(body)["status"] == "healthy"
        print(
            "PASS: packaged api.index cold start, DATABASE_URL unset, /api/health 200"
        )


if __name__ == "__main__":
    asyncio.run(check())
