"""FastAPI middleware for request logging, API key auth, and rate limiting."""

import json
import logging
import time
import uuid
from collections import defaultdict, deque
from typing import Deque, Dict, Iterable, Optional

from fastapi import HTTPException, Request
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from backend.config import settings

logger = logging.getLogger("slopesense.api")


RATE_LIMITS = {
    "public": 100,
    "research": 1000,
    "paid": 10000,
}

PROTECTED_PREFIXES = (
    "/v1/contacts/register",
    "/v1/districts/",
)

_memory_windows: Dict[str, Deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _json_response(status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail})


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Structured request/response logging."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        start = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                json.dumps(
                    {
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status": status_code,
                        "latency_ms": latency_ms,
                        "client_ip": _client_ip(request),
                    }
                )
            )


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Validates X-API-Key for protected endpoints when API keys are configured."""

    def __init__(self, app, protected_prefixes: Iterable[str] = PROTECTED_PREFIXES):
        super().__init__(app)
        self.protected_prefixes = tuple(protected_prefixes)

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        requires_key = any(path.startswith(prefix) for prefix in self.protected_prefixes)
        configured_keys = set(settings.api_key_list)

        if requires_key and settings.is_production and not configured_keys:
            return _json_response(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "API key authentication is not configured",
            )

        if requires_key and configured_keys:
            api_key = request.headers.get("x-api-key")
            if api_key not in configured_keys:
                return _json_response(401, "Missing or invalid API key")

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-backed sliding window rate limiter with in-memory fallback."""

    def __init__(self, app, redis_url: Optional[str] = None, window_seconds: int = 3600):
        super().__init__(app)
        self.redis_url = redis_url
        self.window_seconds = window_seconds
        self.redis = None

    async def _get_redis(self):
        if self.redis is not None:
            return self.redis
        if not self.redis_url:
            return None
        try:
            import redis.asyncio as redis

            self.redis = redis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)
            await self.redis.ping()
            return self.redis
        except Exception as exc:
            logger.warning("Rate limiter using memory fallback: %s", exc)
            self.redis = False
            return None

    def _plan_for_request(self, request: Request) -> str:
        return request.headers.get("x-api-plan", "public").lower()

    def _limit_for_request(self, request: Request) -> int:
        return RATE_LIMITS.get(self._plan_for_request(request), RATE_LIMITS["public"])

    async def _allow_redis(self, key: str, limit: int, now: float) -> bool:
        redis = await self._get_redis()
        if not redis:
            return self._allow_memory(key, limit, now)

        cutoff = now - self.window_seconds
        pipe = redis.pipeline()
        pipe.zremrangebyscore(key, 0, cutoff)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, self.window_seconds)
        _, _, count, _ = await pipe.execute()
        return int(count) <= limit

    def _allow_memory(self, key: str, limit: int, now: float) -> bool:
        window = _memory_windows[key]
        cutoff = now - self.window_seconds
        while window and window[0] < cutoff:
            window.popleft()
        window.append(now)
        return len(window) <= limit

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS" or request.url.path in {"/", "/docs", "/openapi.json"}:
            return await call_next(request)

        now = time.time()
        api_key = request.headers.get("x-api-key", "anonymous")
        key = f"ratelimit:{self._plan_for_request(request)}:{api_key}:{_client_ip(request)}"
        if not await self._allow_redis(key, self._limit_for_request(request), now):
            return _json_response(429, "Rate limit exceeded")

        return await call_next(request)
