"""
Monitoring endpoints — readiness and liveness probes.

Provides:
  - /ready: Readiness probe (200 when all dependencies are available)
  - /live: Liveness probe (200 if process is alive, for k8s/Docker)

Note: The basic /health endpoint is in health.py.
"""
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from backend.api.v1.openapi import code_samples, standard_error_responses
from backend.config import settings
from backend.database import SessionLocal

router = APIRouter()


class ComponentStatus(BaseModel):
    name: str
    status: Literal["up", "down"]
    latency_ms: float | None = None
    message: str | None = None


class ReadinessResponse(BaseModel):
    ready: bool
    timestamp: str
    components: list[ComponentStatus]


class LivenessResponse(BaseModel):
    alive: bool
    timestamp: str
    uptime_seconds: float


_start_time = datetime.now(timezone.utc)


def _check_database() -> ComponentStatus:
    """Check database connectivity."""
    start = datetime.now(timezone.utc)
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            return ComponentStatus(
                name="database",
                status="up",
                latency_ms=round(latency, 1),
            )
        finally:
            db.close()
    except Exception as e:
        return ComponentStatus(
            name="database",
            status="down",
            message=str(e),
        )


def _check_websocket_manager() -> ComponentStatus:
    """Check WebSocket connection manager."""
    try:
        from backend.main import connection_manager
        online_count = connection_manager.online_count
        return ComponentStatus(
            name="websocket",
            status="up",
            message=f"{online_count} active connections",
        )
    except Exception as e:
        return ComponentStatus(
            name="websocket",
            status="down",
            message=str(e),
        )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description=(
        "Returns 200 when all critical dependencies (database, WebSocket) "
        "are available. Use this to determine if the service can accept traffic."
    ),
    responses=standard_error_responses(
        success_model=ReadinessResponse,
        success_description="Service is ready to accept traffic.",
        include_not_found=False,
        include_bad_request=False,
    ),
    openapi_extra=code_samples(
        {
            "lang": "curl",
            "source": "curl 'http://localhost:8000/api/v1/ready'",
        }
    ),
    tags=["monitoring"],
)
def readiness() -> ReadinessResponse:
    """Readiness probe — 200 when all critical dependencies are available."""
    components = [
        _check_database(),
        _check_websocket_manager(),
    ]

    ready = any(c.status == "up" for c in components if c.name == "database")

    return ReadinessResponse(
        ready=ready,
        timestamp=datetime.now(timezone.utc).isoformat(),
        components=components,
    )


@router.get(
    "/live",
    response_model=LivenessResponse,
    summary="Liveness probe",
    description=(
        "Returns 200 if the process is alive. Use this for Docker health "
        "checks and Kubernetes liveness probes."
    ),
    responses=standard_error_responses(
        success_model=LivenessResponse,
        success_description="Service is alive.",
        include_not_found=False,
        include_bad_request=False,
    ),
    openapi_extra=code_samples(
        {
            "lang": "curl",
            "source": "curl 'http://localhost:8000/api/v1/live'",
        }
    ),
    tags=["monitoring"],
)
def liveness() -> LivenessResponse:
    """Liveness probe — 200 if process is alive."""
    uptime = (datetime.now(timezone.utc) - _start_time).total_seconds()

    return LivenessResponse(
        alive=True,
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime_seconds=round(uptime, 1),
    )
