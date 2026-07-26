"""Audit logging middleware — records every mutating request to the AuditLog table."""
from __future__ import annotations

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from backend.database.session import SessionLocal
from backend.models.ai import AuditLog


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Fire-and-forget audit logger for mutating HTTP methods."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)

        # Only log mutating methods
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            self._write_log(request, response.status_code, elapsed_ms)

        return response

    @staticmethod
    def _write_log(request: Request, status_code: int, elapsed_ms: float) -> None:  # noqa: C901
        """Best-effort write to AuditLog.  Never blocks the response."""
        try:
            db = SessionLocal()
            try:
                log = AuditLog(
                    action=request.url.path,
                    query_text=f"{request.method} {request.url.path} -> {status_code} ({elapsed_ms}ms)",
                    result_count=1,
                    ip_address=request.client.host if request.client else None,
                )
                db.add(log)
                db.commit()
            finally:
                db.close()
        except Exception:  # noqa: BLE001 – best-effort logging, never crash the app
            pass
