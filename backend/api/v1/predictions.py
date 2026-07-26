"""
Prediction / ML intelligence endpoints.

  - ``GET  /api/v1/predictions/hotspots``
  - ``GET  /api/v1/predictions/trends``
  - ``GET  /api/v1/predictions/repeat-offenders``
  - ``GET  /api/v1/predictions/clusters``
  - ``GET  /api/v1/predictions/risk-score/{case_id}``
  - ``POST /api/v1/predictions/similar-cases``
  - ``GET  /api/v1/predictions/recommendations/{case_id}``

Every route is a thin pass-through to
:class:`PredictionService`. No business logic lives here.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.v1.openapi import code_samples
from backend.config.logging import get_logger
from backend.database import get_db
from backend.schemas.common import ErrorDetail
from backend.schemas.prediction import (
    PredictionEnvelope,
)
from backend.services.prediction_service import (
    CaseNotTrainedError,
    PredictionService,
)

log = get_logger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _not_found(case_id: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=ErrorDetail(
            code="CASE_NOT_FOUND",
            message=f"Case {case_id} not found",
            details={"case_id": case_id},
        ).model_dump(),
    )


def _svc(db: Session) -> PredictionService:
    return PredictionService(db)


# ---------------------------------------------------------------------
# Request / response helpers
# ---------------------------------------------------------------------


class SimilarCasesRequest(BaseModel):
    """POST body for the similar-cases endpoint."""

    case_id: int = Field(..., ge=1, description="CaseMasterID to find similar cases for")
    top_k: int = Field(default=10, ge=1, le=50, description="Max results")


# ---------------------------------------------------------------------
# GET /predictions/hotspots
# ---------------------------------------------------------------------


@router.get(
    "/hotspots",
    summary="Crime hotspot predictions",
    description=(
        "Returns the top predicted crime hotspots — "
        "(district, crime_head, month) combinations with elevated risk.\n\n"
        "**Query params:**\n"
        "* `top_n` (1-50, default 10) — max results.\n\n"
        "**Example:**\n"
        "```\n"
        "GET /api/v1/predictions/hotspots?top_n=5\n"
        "```"
    ),
    openapi_extra=code_samples(
        {
            "lang": "curl",
            "source": "curl 'http://localhost:8000/api/v1/predictions/hotspots?top_n=5'",
        },
    ),
)
def get_hotspots(
    db: Annotated[Session, Depends(get_db)],
    top_n: Annotated[int, Query(ge=1, le=50)] = 10,
):
    from datetime import datetime, timezone

    hotspots = _svc(db).predict_hotspots(top_n=top_n)
    return PredictionEnvelope(
        generated_at=datetime.now(timezone.utc).isoformat(),
        predictor="hotspot",
        note=f"Top {len(hotspots)} predicted hotspots",
        hotspots=hotspots,
    )


# ---------------------------------------------------------------------
# GET /predictions/trends
# ---------------------------------------------------------------------


@router.get(
    "/trends",
    summary="Crime trend forecasts",
    description=(
        "Returns per-crime-head monthly count forecasts.\n\n"
        "**Query params:**\n"
        "* `horizon_months` (1-12, default 1) — forecast window.\n\n"
        "**Example:**\n"
        "```\n"
        "GET /api/v1/predictions/trends?horizon_months=3\n"
        "```"
    ),
    openapi_extra=code_samples(
        {
            "lang": "curl",
            "source": "curl 'http://localhost:8000/api/v1/predictions/trends?horizon_months=3'",
        },
    ),
)
def get_trends(
    db: Annotated[Session, Depends(get_db)],
    horizon_months: Annotated[int, Query(ge=1, le=12)] = 1,
):
    from datetime import datetime, timezone

    trends = _svc(db).predict_trends(horizon_months=horizon_months)
    return PredictionEnvelope(
        generated_at=datetime.now(timezone.utc).isoformat(),
        predictor="trend",
        note=f"Forecast for {len(trends)} periods",
        trends=trends,
    )


# ---------------------------------------------------------------------
# GET /predictions/repeat-offenders
# ---------------------------------------------------------------------


@router.get(
    "/repeat-offenders",
    summary="Repeat offender predictions",
    description=(
        "Returns accused individuals ranked by reoffending probability.\n\n"
        "**Query params:**\n"
        "* `top_n` (1-100, default 20) — max results.\n\n"
        "**Example:**\n"
        "```\n"
        "GET /api/v1/predictions/repeat-offenders?top_n=10\n"
        "```"
    ),
    openapi_extra=code_samples(
        {
            "lang": "curl",
            "source": "curl 'http://localhost:8000/api/v1/predictions/repeat-offenders?top_n=10'",
        },
    ),
)
def get_repeat_offenders(
    db: Annotated[Session, Depends(get_db)],
    top_n: Annotated[int, Query(ge=1, le=100)] = 20,
):
    from datetime import datetime, timezone

    offenders = _svc(db).predict_repeat_offenders(top_n=top_n)
    return PredictionEnvelope(
        generated_at=datetime.now(timezone.utc).isoformat(),
        predictor="repeat_offender",
        note=f"Top {len(offenders)} at-risk accused",
        repeat_offenders=offenders,
    )


# ---------------------------------------------------------------------
# GET /predictions/clusters
# ---------------------------------------------------------------------


@router.get(
    "/clusters",
    summary="Crime pattern clusters",
    description=(
        "Returns automatically detected crime clusters based on "
        "modus operandi, location, and other features.\n\n"
        "**Query params:**\n"
        "* `top_n` (1-20, default 5) — max clusters.\n\n"
        "**Example:**\n"
        "```\n"
        "GET /api/v1/predictions/clusters?top_n=5\n"
        "```"
    ),
    openapi_extra=code_samples(
        {
            "lang": "curl",
            "source": "curl 'http://localhost:8000/api/v1/predictions/clusters?top_n=5'",
        },
    ),
)
def get_clusters(
    db: Annotated[Session, Depends(get_db)],
    top_n: Annotated[int, Query(ge=1, le=20)] = 5,
):
    from datetime import datetime, timezone

    clusters = _svc(db).cluster_patterns(top_n=top_n)
    return PredictionEnvelope(
        generated_at=datetime.now(timezone.utc).isoformat(),
        predictor="clustering",
        note=f"{len(clusters)} crime clusters detected",
        clusters=clusters,
    )


# ---------------------------------------------------------------------
# GET /predictions/risk-score/{case_id}
# ---------------------------------------------------------------------


@router.get(
    "/risk-score/{case_id}",
    summary="FIR risk score",
    description=(
        "Returns a composite 0-100 risk score for a single FIR, "
        "based on location, crime type, repeat offender risk, "
        "and crime trend data.\n\n"
        "**Path params:**\n"
        "* `case_id` (>=1) - CaseMasterID.\n\n"
        "**Example:**\n"
        "```\n"
        "GET /api/v1/predictions/risk-score/12\n"
        "```"
    ),
    openapi_extra=code_samples(
        {
            "lang": "curl",
            "source": "curl 'http://localhost:8000/api/v1/predictions/risk-score/12'",
        },
    ),
)
def get_risk_score(
    case_id: Annotated[int, Path(ge=1, description="CaseMasterID")],
    db: Annotated[Session, Depends(get_db)],
):
    from datetime import datetime, timezone

    try:
        risk = _svc(db).score_fir_risk(case_id)
    except CaseNotTrainedError as exc:
        raise _not_found(case_id) from exc

    return PredictionEnvelope(
        generated_at=datetime.now(timezone.utc).isoformat(),
        predictor="risk_score",
        note=f"Risk score for FIR {risk.fir_number}",
        risk_score=risk,
    )


# ---------------------------------------------------------------------
# POST /predictions/similar-cases
# ---------------------------------------------------------------------


@router.post(
    "/similar-cases",
    summary="Find semantically similar cases",
    description=(
        "Returns the top-k cases most similar to the given case, "
        "based on MO embedding similarity (TF-IDF + cosine).\n\n"
        "**Body:**\n"
        "```json\n"
        '{"case_id": 12, "top_k": 10}\n'
        "```\n\n"
        "**Example:**\n"
        "```\n"
        "POST /api/v1/predictions/similar-cases\n"
        "```"
    ),
    openapi_extra=code_samples(
        {
            "lang": "curl",
            "source": (
                "curl -X POST 'http://localhost:8000/api/v1/predictions/similar-cases' "
                "-H 'Content-Type: application/json' "
                "-d '{\"case_id\": 12, \"top_k\": 10}'"
            ),
        },
    ),
)
def post_similar_cases(
    body: SimilarCasesRequest,
    db: Annotated[Session, Depends(get_db)],
):
    from datetime import datetime, timezone

    try:
        similar = _svc(db).find_similar_cases(
            case_id=body.case_id, top_k=body.top_k
        )
    except CaseNotTrainedError as exc:
        raise _not_found(body.case_id) from exc

    return PredictionEnvelope(
        generated_at=datetime.now(timezone.utc).isoformat(),
        predictor="similarity",
        note=f"Found {len(similar)} similar cases for case {body.case_id}",
        similar_cases=similar,
    )


# ---------------------------------------------------------------------
# GET /predictions/recommendations/{case_id}
# ---------------------------------------------------------------------


@router.get(
    "/recommendations/{case_id}",
    summary="Officer assignment recommendations",
    description=(
        "Returns recommended officers for a given FIR, based on "
        "crime-head specialisation, district familiarity, and "
        "recent caseload.\n\n"
        "**Path params:**\n"
        "* `case_id` (>=1) - CaseMasterID.\n\n"
        "**Query params:**\n"
        "* `top_n` (1-10, default 3) - max recommendations.\n\n"
        "**Example:**\n"
        "```\n"
        "GET /api/v1/predictions/recommendations/12\n"
        "```"
    ),
    openapi_extra=code_samples(
        {
            "lang": "curl",
            "source": "curl 'http://localhost:8000/api/v1/predictions/recommendations/12'",
        },
    ),
)
def get_recommendations(
    case_id: Annotated[int, Path(ge=1, description="CaseMasterID")],
    db: Annotated[Session, Depends(get_db)],
    top_n: Annotated[int, Query(ge=1, le=10)] = 3,
):
    from datetime import datetime, timezone

    try:
        recs = _svc(db).recommend_officers(case_id=case_id, top_n=top_n)
    except CaseNotTrainedError as exc:
        raise _not_found(case_id) from exc

    return PredictionEnvelope(
        generated_at=datetime.now(timezone.utc).isoformat(),
        predictor="recommendation",
        note=f"{len(recs)} officer(s) recommended for case {case_id}",
        recommendations=recs,
    )
