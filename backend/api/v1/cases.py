"""
Case (FIR) endpoints.

  - ``GET /api/v1/cases``        : paginated, filterable, sortable list
  - ``GET /api/v1/cases/{id}``   : full case detail (one round-trip)

Both routes are thin: they parse and validate query/path parameters,
hand the work to :class:`CaseService`, and shape the response. No
business logic lives here.

OpenAPI documentation for both routes is built through
:func:`backend.api.v1.openapi.standard_error_responses` so the four
required example categories (success, validation, not found, empty)
are always present and consistent across endpoints.
"""
from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from backend.api.v1 import examples
from backend.api.v1.openapi import code_samples, standard_error_responses
from backend.config.logging import get_logger
from backend.database import get_db
from backend.schemas.case import (
    CaseDetailOut,
    CaseListResponse,
    CaseSummaryOut,
)
from backend.schemas.common import ErrorDetail
from backend.services import (
    ALLOWED_SORT_FIELDS,
    CaseFilters,
    CaseNotFoundError,
    CaseService,
    CaseSort,
)
from backend.utils.pagination import calculate_pagination

log = get_logger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _error(code: str, message: str, **details) -> HTTPException:
    """Build a structured 4xx/5xx exception.

    FastAPI's default error envelope (``{"detail": "..."}``) is
    unsuitable for our API contract; we override it to match
    :class:`ErrorResponse` everywhere.
    """
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=ErrorDetail(
            code=code, message=message, details=details or None
        ).model_dump(),
    )


# ---------------------------------------------------------------------
# GET /cases
# ---------------------------------------------------------------------


@router.get(
    "",
    response_model=CaseListResponse,
    summary="List FIRs (cases)",
    description=(
        "Returns a paginated list of FIRs. Supports filtering by FIR "
        "number, district, police station, crime head, crime sub head, "
        "status, and a date range on the registered date. Filters accept "
        "either a name (case-insensitive) or an ID; when both are sent, "
        "the ID wins. Sort is restricted to a whitelist of columns.\n\n"
        "**Example:**\n"
        "```\n"
        "GET /api/v1/cases?district=Bengaluru%20Urban&page=1&page_size=5\n"
        "```"
    ),
    responses=standard_error_responses(
        success_model=CaseListResponse,
        success_description="Paginated list of cases.",
        success_examples={
            "success": examples.EXAMPLE_LIST_SUCCESS,
            "filtered": examples.EXAMPLE_LIST_FILTERED,
            # Empty results live under success because the HTTP status
            # is 200 — the only way to distinguish them in Swagger is
            # via the example name in the dropdown.
            "empty_results": examples.EXAMPLE_LIST_EMPTY,
        },
        bad_request_description="Invalid sort field or order.",
        bad_request_examples={
            "invalid_sort_field": examples.EXAMPLE_INVALID_SORT_FIELD,
            "invalid_sort_order": examples.EXAMPLE_INVALID_SORT_ORDER,
        },
        include_not_found=False,  # list endpoints never 404
    ),
    openapi_extra=code_samples(
        {
            "lang": "curl",
            "source": (
                "curl -G 'http://localhost:8000/api/v1/cases' "
                "--data-urlencode 'district=Bengaluru Urban' "
                "--data-urlencode 'page=1' "
                "--data-urlencode 'page_size=5' "
                "--data-urlencode 'sort_by=crime_registered_date' "
                "--data-urlencode 'sort_order=desc'"
            ),
        }
    ),
)
def list_cases(
    db: Annotated[Session, Depends(get_db)],
    fir_number: Annotated[
        str | None,
        Query(description="Exact FIR number (e.g. 104430001202400001)"),
    ] = None,
    district: Annotated[
        str | None,
        Query(description="District name (case-insensitive)"),
    ] = None,
    district_id: Annotated[
        int | None,
        Query(ge=1, description="District ID (takes precedence over name)"),
    ] = None,
    police_station: Annotated[
        str | None,
        Query(description="Police station name (case-insensitive)"),
    ] = None,
    police_station_id: Annotated[
        int | None,
        Query(ge=1, description="Police station (Unit) ID"),
    ] = None,
    crime_head: Annotated[
        str | None,
        Query(description="Crime head (crime group) name"),
    ] = None,
    crime_head_id: Annotated[
        int | None, Query(ge=1, description="Crime head ID")
    ] = None,
    crime_sub_head: Annotated[
        str | None,
        Query(description="Crime sub head (specific crime) name"),
    ] = None,
    crime_sub_head_id: Annotated[
        int | None, Query(ge=1, description="Crime sub head ID")
    ] = None,
    status_name: Annotated[
        str | None,
        Query(
            alias="status",
            description="Case status name (Open, Under Investigation, "
            "Charge Sheeted, Closed, Undetected)",
        ),
    ] = None,
    status_id: Annotated[
        int | None, Query(ge=1, description="Case status ID")
    ] = None,
    date_from: Annotated[
        date | None,
        Query(description="Earliest CrimeRegisteredDate (inclusive)"),
    ] = None,
    date_to: Annotated[
        date | None,
        Query(description="Latest CrimeRegisteredDate (inclusive)"),
    ] = None,
    page: Annotated[int, Query(ge=1, description="1-based page number")] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=100, description="Items per page (max 100)"),
    ] = 20,
    sort_by: Annotated[
        str,
        Query(
            description=(
                "Whitelisted sort field. One of: "
                + ", ".join(sorted(ALLOWED_SORT_FIELDS))
            )
        ),
    ] = "crime_registered_date",
    sort_order: Annotated[
        str,
        Query(description="Sort direction: asc or desc"),
    ] = "desc",
) -> CaseListResponse:
    # ---- 1. validate sort ------------------------------------------
    if sort_by not in ALLOWED_SORT_FIELDS:
        raise _error(
            code="INVALID_SORT_FIELD",
            message=(
                f"sort_by={sort_by!r} is not allowed. "
                f"Allowed values: {sorted(ALLOWED_SORT_FIELDS)}"
            ),
            allowed=sorted(ALLOWED_SORT_FIELDS),
        )
    if sort_order not in ("asc", "desc"):
        raise _error(
            code="INVALID_SORT_ORDER",
            message=f"sort_order={sort_order!r} must be 'asc' or 'desc'",
            allowed=["asc", "desc"],
        )

    # ---- 2. build filter + service call ----------------------------
    filters = CaseFilters(
        fir_number=fir_number,
        district=district,
        district_id=district_id,
        police_station=police_station,
        police_station_id=police_station_id,
        crime_head=crime_head,
        crime_head_id=crime_head_id,
        crime_sub_head=crime_sub_head,
        crime_sub_head_id=crime_sub_head_id,
        status=status_name,
        status_id=status_id,
        date_from=date_from,
        date_to=date_to,
    )
    sort = CaseSort(field=sort_by, order=sort_order)

    service = CaseService(db)
    rows, total = service.list_cases(
        filters=filters, page=page, page_size=page_size, sort=sort
    )

    # ---- 3. shape response -----------------------------------------
    items = [CaseSummaryOut.model_validate(r) for r in rows]
    meta = calculate_pagination(
        page=page, page_size=page_size, total=total
    )
    log.info(
        "list_cases page=%s size=%s total=%s returned=%s",
        page,
        page_size,
        total,
        len(items),
    )
    return CaseListResponse.build(items=items, meta=meta)


# ---------------------------------------------------------------------
# GET /cases/{case_id}
# ---------------------------------------------------------------------


@router.get(
    "/{case_id}",
    response_model=CaseDetailOut,
    summary="Get one FIR with all related records",
    description=(
        "Returns the case plus its complainant, victims, accused, "
        "evidence, recovered items, chargesheet, act & sections, and "
        "assigned officers.\n\n"
        "**Example:**\n"
        "```\n"
        "GET /api/v1/cases/12\n"
        "```"
    ),
    responses=standard_error_responses(
        success_model=CaseDetailOut,
        success_description="Full case detail.",
        success_examples={
            "success": examples.EXAMPLE_DETAIL_SUCCESS,
        },
        include_bad_request=False,  # case_id has only validation
        not_found_description="Case not found.",
        not_found_examples={
            "not_found": examples.EXAMPLE_CASE_NOT_FOUND,
        },
    ),
    openapi_extra=code_samples(
        {
            "lang": "curl",
            "source": "curl 'http://localhost:8000/api/v1/cases/12'",
        }
    ),
)
def get_case(
    case_id: Annotated[int, Path(ge=1, description="CaseMasterID")],
    db: Annotated[Session, Depends(get_db)],
) -> CaseDetailOut:
    try:
        case = CaseService(db).get_case_detail(case_id)
    except CaseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code="CASE_NOT_FOUND",
                message=str(exc),
                details={"case_id": exc.case_id},
            ).model_dump(),
        ) from exc

    return CaseDetailOut.model_validate(case)
