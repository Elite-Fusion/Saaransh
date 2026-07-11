"""
Health-check endpoint.

Phase 2 update: always returns HTTP 200.
The database reachability is reported in the JSON body (`database: up|down`)
so monitoring tools can read the field, but the HTTP status itself never
changes — this keeps liveness probes simple and avoids restart loops when
the DB is briefly unreachable.

Phase 3.5 update: full OpenAPI documentation — success + degraded
examples and a curl code sample.
"""
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from backend.api.v1 import examples
from backend.api.v1.openapi import code_samples, standard_error_responses
from backend.config import settings
from backend.database import SessionLocal

router = APIRouter()


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    environment: str
    database: Literal["up", "down"]
    timestamp: str


def _check_database() -> Literal["up", "down"]:
    """Run SELECT 1 in a fresh session, swallow any error."""
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return "up"
    except Exception:
        return "down"
    finally:
        db.close()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health probe",
    description=(
        "Returns 200 OK as long as the API process is running. The "
        "`database` field is `up` when a `SELECT 1` round-trip "
        "succeeds, otherwise `down`.\n\n"
        "**Example:**\n"
        "```\n"
        "GET /api/v1/health\n"
        "```"
    ),
    responses=standard_error_responses(
        success_model=HealthResponse,
        success_examples={
            "healthy": examples.EXAMPLE_HEALTH_SUCCESS,
            "degraded_db_down": examples.EXAMPLE_HEALTH_DEGRADED,
        },
        success_description=(
            "Service is running. The `database` field is `up` if the "
            "DB is reachable, `down` otherwise."
        ),
        # Health probe has no 400 / 404 / 422 outcomes — disable them.
        include_bad_request=False,
        include_not_found=False,
        include_validation=False,
    ),
    openapi_extra=code_samples(
        {
            "lang": "curl",
            "source": "curl 'http://localhost:8000/api/v1/health'",
        }
    ),
)
def healthcheck() -> HealthResponse:
    db_status = _check_database()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        database=db_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
