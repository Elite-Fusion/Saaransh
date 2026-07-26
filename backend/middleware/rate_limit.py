"""
Rate limiting middleware — basic in-memory rate limiting.

Uses a simple token bucket algorithm per IP address.
For production, consider using Redis-backed rate limiting.
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Basic rate limiting middleware.

    Args:
        requests_per_minute: Maximum requests per minute per IP.
        burst: Maximum burst size before rate limiting kicks in.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        burst: int = 10,
    ) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst = burst
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP, respecting X-Forwarded-For header."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _is_rate_limited(self, client_ip: str) -> bool:
        """Check if client has exceeded rate limit."""
        now = time.time()
        window_start = now - 60  # 1 minute window

        # Clean old requests
        self._requests[client_ip] = [
            t for t in self._requests[client_ip] if t > window_start
        ]

        # Check if rate limit exceeded
        if len(self._requests[client_ip]) >= self.requests_per_minute:
            return True

        # Add current request
        self._requests[client_ip].append(now)
        return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ("/api/v1/health", "/api/v1/live", "/api/v1/ready"):
            return await call_next(request)

        client_ip = self._get_client_ip(request)

        if self._is_rate_limited(client_ip):
            return JSONResponse(
                status_code=429,
                content={
                    "detail": {
                        "code": "rate_limit_exceeded",
                        "message": "Too many requests. Please try again later.",
                    }
                },
            )

        return await call_next(request)
