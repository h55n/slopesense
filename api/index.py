import os
import sys

# Add the project root to sys.path so that 'backend' module is resolvable
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

from backend.api.main import app as _app

async def app(scope, receive, send):
    if scope["type"] in ["http", "websocket"]:
        path = scope.get("path", "")
        if path.startswith("/api"):
            scope["path"] = path[4:] or "/"
            scope["root_path"] = "/api"
    return await _app(scope, receive, send)
