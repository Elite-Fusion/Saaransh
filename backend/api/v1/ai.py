"""
AI investigation endpoints.

- ``POST /api/v1/ai/investigate`` : run the full investigation pipeline
  and return a structured response.

The endpoint is thin: it validates the request, hands the work to
:class:`InvestigationService`, and shapes the response. No business logic
lives here.

OpenAPI documentation for the route is built through
:func:`backend.api.v1.openapi.standard_error_responses` so the four
required example categories (success, validation, not found, empty) are
always present and consistent across endpoints.
"""
from __future__ import annotations

from typing import Annotated, Any


from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.v1 import examples
from backend.api.v1.openapi import code_samples, standard_error_responses
from backend.config.logging import get_logger
from backend.database import get_db

# AI services
from backend.ai.services.investigation_service import InvestigationService
from backend.ai.services.chat_service import ChatService
from backend.ai.services.intent_service import IntentService
from backend.ai.services.sql_generation_service import SQLGenerationService
from backend.ai.services.sql_validation_service import SQLValidationService
from backend.ai.services.exceptions import UnknownIntent, UnsafeSQL
from backend.ai.providers.factory import get_provider
from backend.ai.services.prompt_service import get_prompt_service
from backend.services.ai_query_service import AIQueryService
from backend.services import CaseService, AnalyticsService, CaseNotFoundError

# AI response schema
from backend.ai.schemas.ai import InvestigationResponse

log = get_logger(__name__)
router = APIRouter()


class InvestigationRequest(BaseModel):
    """Request body for the investigation endpoint."""
    question: str = Field(..., example="Show me theft cases in Mumbai from last month")
    request_id: str = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    metadata: dict[str, Any] | None = Field(default=None, description="Optional conversation metadata (session_id, active_case_id).")


InvestigationRequest.model_rebuild()




def _error(code: str, message: str, **details) -> HTTPException:
    """Build a structured 4xx/5xx exception.

    FastAPI's default error envelope (``{"detail": "..."}``) is unsuitable
    for our API contract; we override it to match :class:`ErrorResponse`
    everywhere.
    """
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "code": code,
            "message": message,
            "details": details or None,
        },
    )


@router.post(
    "/investigate",
    response_model=InvestigationResponse,
    summary="Run a criminal investigation query",
    description=(
        "Accepts a natural-language question about crime data, runs the "
        "full AI investigation pipeline (intent classification, optional SQL "
        "generation/validation/execution, explanation), and returns a "
        "structured response that includes the answer, explanation, and "
        "supporting evidence."
    ),
    responses=standard_error_responses(
        success_model=InvestigationResponse,
        success_examples={
            "success": {
                "summary": "200 — successful investigation",
                "description": (
                    "The question was understood, processed, and a response "
                    "generated. The `confidence` score indicates the "
                    "system's certainty in the answer."
                ),
                "value": {
                    "request_id": "123e4567-e89b-12d3-a456-426614174000",
                    "intent": "case_search",
                    "operation": "service",
                    "reasoning": "Question classified as case_search "
                                 "(keywords: crime, theft, Mumbai). "
                                 "Operation: CaseService.list_cases.",
                    "executed_operation": "CaseService.list_cases",
                    "confidence": 0.85,
                    "assumptions": ["No date range provided; assumes all time."],
                    "supporting_evidence": [
                        {
                            "case_id": 101,
                            "fir_number": "104430001202400001",
                            "label": "Case: 202400001; Status: Under Investigation"
                        }
                    ],
                    "explanation": {
                        "summary": "Found 1 matching case from Jan 2024 to present.",
                        "evidence": [
                            {
                                "case_id": 101,
                                "fir_number": "104430001202400001",
                                "label": "Case: 202400001; Status: Under Investigation"
                            }
                        ],
                        "why": "The query asked for recent theft cases in Mumbai. "
                               "The system matched the crime head 'Theft' and "
                               "returned the most recent case.",
                        "confidence": "high",
                        "confidence_score": 0.85,
                        "confidence_reason": "High confidence due to exact match "
                                             "on crime head and recent date.",
                        "caveats": ["Does not include sealed cases."]
                    },
                    "raw_sql": None,
                    "raw_params": None,
                    "row_count": 1,
                    "columns": [
                        "CaseMasterID",
                        "CrimeNo",
                        "CrimeRegisteredDate",
                        "case_status",
                        "crime_major_head",
                    ],
                    "placeholder": None,
                }
            },
        },
        not_found_examples={
            "not_found": {
                "summary": "404 — case not found (for explain_case intent)",
                "description": (
                    "When the intent is EXPLAIN_CASE but the supplied case ID "
                    "does not exist in the database."
                ),
                "value": {
                    "detail": {
                        "code": "CASE_NOT_FOUND",
                        "message": "Case 99999 not found",
                        "details": {"case_id": 99999},
                    }
                }
            }
        },
        bad_request_examples={
            "invalid_intent": {
                "summary": "400 — invalid intent classification",
                "description": (
                    "Returned when the intent classifier cannot determine a "
                    "valid intent and the regex fallback also fails."
                ),
                "value": {
                    "detail": {
                        "code": "UNKNOWN_INTENT",
                        "message": "Could not determine intent from question: "
                                   "'blah blah blah'.",
                        "details": {"question": "blah blah blah"},
                    }
                }
            },
            "unsafe_sql": {
                "summary": "400 — SQL validation failed",
                "description": (
                    "Returned when the SQL validator rejects the generated "
                    "SQL as unsafe (non‑SELECT or disallowed table/column)."
                ),
                "value": {
                    "detail": {
                        "code": "UNSAFE_SQL",
                        "message": "SQL validation failed: DELETE not allowed",
                        "details": {
                            "sql": "DELETE FROM case_master WHERE 1=1",
                            "category": "verb",
                        },
                    }
                }
            }
        },
        include_validation=True,
    ),
    openapi_extra=code_samples(
        {
            "lang": "curl",
            "source": (
                "curl -X POST 'http://localhost:8000/api/v1/ai/investigate' "
                "-H 'Content-Type: application/json' "
                "-d '{\"question\": \"Show me theft cases in Mumbai from last month\", "
                "\"request_id\": \"123e4567-e89b-12d3-a456-426614174000\"}'"
            )
        }
    ),
)
def investigate(
    db: Annotated[Session, Depends(get_db)],
    request: InvestigationRequest = Body(...),
) -> InvestigationResponse:
    """Run the investigation pipeline and return the structured response.

    Args:
        request: The request body containing the question and request ID.
        db: SQLAlchemy session (provided by dependency injection).

    Returns:
        A populated :class:`InvestigationResponse`.

    Raises:
        HTTPException: 400 for bad input (unknown intent, unsafe SQL),
                       422 for validation errors (handled by FastAPI),
                       500 for unexpected internal errors.
    """
    try:
        # Instantiate the dependent services
        provider = get_provider()
        prompt_service = get_prompt_service()
        chat_service = ChatService(provider=provider, prompt_service=prompt_service)
        intent_service = IntentService(chat_service=chat_service)
        sql_gen_service = SQLGenerationService(chat_service=chat_service)
        sql_val_service = SQLValidationService()
        ai_query_service = AIQueryService(db)
        # Optional services: case and analytics are created inside InvestigationService
        # if not provided, but we can pass them explicitly for clarity.
        case_service = CaseService(db)
        analytics_service = AnalyticsService(db)

        # Create the investigation service
        inv_service = InvestigationService(
            session=db,
            chat_service=chat_service,
            intent_service=intent_service,
            sql_generation_service=sql_gen_service,
            sql_validation_service=sql_val_service,
            ai_query_service=ai_query_service,
            case_service=case_service,
            analytics_service=analytics_service,
            logger=log,
        )

        # Run the investigation
        result = inv_service.investigate(
            question=request.question,
            request_id=request.request_id,
            metadata=request.metadata,
        )


        return result

    except UnknownIntent as exc:
        # Unknown intent from the classifier or regex fallback
        # Format message to match OpenAPI documentation expectations
        question = exc.question if hasattr(exc, 'question') else "unknown"
        message = f"Could not determine intent from question: {question!r}."
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "UNKNOWN_INTENT",
                "message": message,
                "details": {"question": question},
            },
        ) from exc
    except UnsafeSQL as exc:
        # SQL validation failed
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "UNSAFE_SQL",
                "message": str(exc),
                "details": {
                    "sql": exc.sql if hasattr(exc, 'sql') else None,
                    "category": exc.category if hasattr(exc, 'category') else None,
                },
            },
        ) from exc
    except CaseNotFoundError as exc:
        # Case not found for explain_case intent
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CASE_NOT_FOUND",
                "message": str(exc),
                "details": {"case_id": exc.case_id if hasattr(exc, 'case_id') else None},
            },
        ) from exc
    except Exception as exc:
        # Catch any unexpected error and return 500
        log.exception("Unhandled exception in investigation endpoint")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred.",
                "details": {"error": str(exc)},
            },
        ) from exc