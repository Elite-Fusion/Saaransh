"""
Dashboard / analytics endpoints.

  - ``GET /api/v1/dashboard/summary``
  - ``GET /api/v1/dashboard/monthly-trends``
  - ``GET /api/v1/dashboard/crime-head-distribution``
  - ``GET /api/v1/dashboard/status-distribution``
  - ``GET /api/v1/dashboard/district-distribution``
  - ``GET /api/v1/dashboard/recent-cases``

Every route is a thin pass-through to :class:`AnalyticsService`. No
business logic lives here — parameter parsing, response shaping,
OpenAPI documentation only.

OpenAPI metadata is built with the helpers in
:mod:`backend.api.v1.openapi`, so the four required example
categories (success, empty, validation, not-found) are always present.
"""
from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.api.v1 import examples
from backend.api.v1.openapi import code_samples, standard_error_responses
from backend.config.logging import get_logger
from backend.database import get_db
from backend.schemas.case import CaseSummaryOut
from backend.schemas.common import PaginationMeta
from backend.schemas.dashboard import (
    CategoryDistributionResponse,
    CategoryCountOut,
    DashboardSummaryOut,
    DistrictRefOut,
    MonthlyTrendPoint,
    MonthlyTrendsResponse,
    RecentCasesResponse,
)
from backend.services.analytics_service import (
    AnalyticsService,
    DistrictRef,
)
from backend.utils.pagination import calculate_pagination

log = get_logger(__name__)
router = APIRouter()

# Calendar-month labels — used to attach a "Jan", "Feb", … string to
# each monthly trend point so the front-end can render the chart
# without needing a separate date library.
_MONTH_LABELS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

# Valid CaseStatus ids that the summary endpoint aggregates. Not used
# as a hard validator — the service bucketises by name — kept here as
# documentation for the OpenAPI description.


# ---------------------------------------------------------------------
# /summary
# ---------------------------------------------------------------------


@router.get(
    "/summary",
    response_model=DashboardSummaryOut,
    summary="Dashboard summary tile",
    description=(
        "Returns the six headline counts. `convictions` and "
        "`acquittals` are always 0 in the current schema — verdict "
        "data is not yet tracked. The fields exist in the contract "
        "so the React UI and the Gemini AI provider can rely on the "
        "shape.\n\n"
        "**Optional district filter** — pass `district` (name) or "
        "`district_id`; when both are sent the id wins.\n\n"
        "**Example:**\n"
        "```\n"
        "GET /api/v1/dashboard/summary\n"
        "```"
    ),
    responses=standard_error_responses(
        success_model=DashboardSummaryOut,
        success_description=(
            "Six headline counters. `convictions` and `acquittals` "
            "are always 0 — verdict data is not yet tracked."
        ),
        success_examples={
            "normal": examples.EXAMPLE_SUMMARY_NORMAL,
            "empty": examples.EXAMPLE_SUMMARY_ZEROS,
        },
        include_not_found=False,  # summary never 404s
    ),
    openapi_extra=code_samples(
        {
            "lang": "curl",
            "source": "curl 'http://localhost:8000/api/v1/dashboard/summary'",
        },
        {
            "lang": "curl",
            "source": (
                "curl 'http://localhost:8000/api/v1/dashboard/summary"
                "?district=Mysuru'"
            ),
        },
    ),
)
def get_summary(
    db: Annotated[Session, Depends(get_db)],
    district: Annotated[
        str | None,
        Query(description="Filter by district name (case-insensitive)"),
    ] = None,
    district_id: Annotated[
        int | None, Query(ge=1, description="Filter by district id")
    ] = None,
) -> DashboardSummaryOut:
    ref = DistrictRef(name=district, district_id=district_id)
    summary = AnalyticsService(db).get_summary(district=ref)
    return DashboardSummaryOut(
        total_cases=summary.total_cases,
        open_cases=summary.open_cases,
        closed_cases=summary.closed_cases,
        charge_sheet_filed=summary.charge_sheet_filed,
        convictions=summary.convictions,
        acquittals=summary.acquittals,
    )


# ---------------------------------------------------------------------
# /monthly-trends
# ---------------------------------------------------------------------


@router.get(
    "/monthly-trends",
    response_model=MonthlyTrendsResponse,
    summary="Monthly case-registration trends",
    description=(
        "Returns 12 monthly counts (Jan..Dec) for the given `year`. "
        "Months with no cases are returned as `case_count: 0` so the "
        "chart always has 12 data points. Optional district filter.\n\n"
        "**Example:**\n"
        "```\n"
        "GET /api/v1/dashboard/monthly-trends?year=2024\n"
        "```"
    ),
    responses=standard_error_responses(
        success_model=MonthlyTrendsResponse,
        success_description=(
            "Twelve monthly counts for the requested year; missing "
            "months are zero-filled."
        ),
        success_examples={
            "normal": examples.EXAMPLE_MONTHLY_NORMAL,
            "filtered": examples.EXAMPLE_MONTHLY_FILTERED,
            "empty": examples.EXAMPLE_MONTHLY_EMPTY,
        },
        include_not_found=False,
    ),
    openapi_extra=code_samples(
        {
            "lang": "curl",
            "source": (
                "curl 'http://localhost:8000/api/v1/dashboard/monthly-trends"
                "?year=2024'"
            ),
        },
        {
            "lang": "curl",
            "source": (
                "curl 'http://localhost:8000/api/v1/dashboard/monthly-trends"
                "?year=2024&district=Mysuru'"
            ),
        },
    ),
)
def get_monthly_trends(
    db: Annotated[Session, Depends(get_db)],
    year: Annotated[
        int,
        Query(
            ge=1900,
            le=2200,
            description="Calendar year to aggregate over.",
        ),
    ] = date.today().year,
    district: Annotated[
        str | None,
        Query(description="Filter by district name (case-insensitive)"),
    ] = None,
    district_id: Annotated[
        int | None, Query(ge=1, description="Filter by district id")
    ] = None,
) -> MonthlyTrendsResponse:
    ref = DistrictRef(name=district, district_id=district_id)
    trends = AnalyticsService(db).get_monthly_trends(year=year, district=ref)

    # Resolve the district filter echo (id + name). If a name was
    # given and didn't resolve, the service already short-circuited
    # to all zeros — surface that honestly.
    district_echo: DistrictRefOut | None = None
    if district_id is not None:
        district_echo = _lookup_district(db, district_id=district_id)
    elif district is not None:
        district_echo = _lookup_district(db, name=district)

    items = [
        MonthlyTrendPoint(
            year=trend.year,
            month=trend.month,
            month_label=_MONTH_LABELS[trend.month - 1],
            case_count=trend.case_count,
        )
        for trend in trends
    ]
    return MonthlyTrendsResponse(
        year=year,
        district=district_echo,
        items=items,
    )


# ---------------------------------------------------------------------
# /crime-head-distribution
# ---------------------------------------------------------------------


@router.get(
    "/crime-head-distribution",
    response_model=CategoryDistributionResponse,
    summary="Cases grouped by Crime Head",
    description=(
        "Returns one row per Crime Head, including the count. "
        "Optional district filter.\n\n"
        "**Example:**\n"
        "```\n"
        "GET /api/v1/dashboard/crime-head-distribution\n"
        "```"
    ),
    responses=standard_error_responses(
        success_model=CategoryDistributionResponse,
        success_description=(
            "One row per Crime Head, with the count."
        ),
        success_examples={
            "normal": examples.EXAMPLE_CRIME_HEAD_NORMAL,
            "filtered": examples.EXAMPLE_CRIME_HEAD_FILTERED,
            "empty": examples.EXAMPLE_CRIME_HEAD_EMPTY,
        },
        include_not_found=False,
    ),
    openapi_extra=code_samples(
        {
            "lang": "curl",
            "source": (
                "curl 'http://localhost:8000/api/v1/dashboard/"
                "crime-head-distribution'"
            ),
        },
        {
            "lang": "curl",
            "source": (
                "curl 'http://localhost:8000/api/v1/dashboard/"
                "crime-head-distribution?district=Bengaluru%20Urban'"
            ),
        },
    ),
)
def get_crime_head_distribution(
    db: Annotated[Session, Depends(get_db)],
    district: Annotated[
        str | None,
        Query(description="Filter by district name (case-insensitive)"),
    ] = None,
    district_id: Annotated[
        int | None, Query(ge=1, description="Filter by district id")
    ] = None,
) -> CategoryDistributionResponse:
    ref = DistrictRef(name=district, district_id=district_id)
    rows = AnalyticsService(db).get_crime_head_distribution(district=ref)
    return _to_distribution_response(rows)


# ---------------------------------------------------------------------
# /status-distribution
# ---------------------------------------------------------------------


@router.get(
    "/status-distribution",
    response_model=CategoryDistributionResponse,
    summary="Cases grouped by Case Status",
    description=(
        "Returns one row per Case Status. No filter — this is a "
        "global distribution. The five seed statuses are Open, "
        "Under Investigation, Charge Sheeted, Closed, Undetected.\n\n"
        "**Example:**\n"
        "```\n"
        "GET /api/v1/dashboard/status-distribution\n"
        "```"
    ),
    responses=standard_error_responses(
        success_model=CategoryDistributionResponse,
        success_description="One row per Case Status, with the count.",
        success_examples={
            "normal": examples.EXAMPLE_STATUS_NORMAL,
            "empty": examples.EXAMPLE_STATUS_EMPTY,
        },
        include_not_found=False,
    ),
    openapi_extra=code_samples(
        {
            "lang": "curl",
            "source": (
                "curl 'http://localhost:8000/api/v1/dashboard/status-distribution'"
            ),
        },
    ),
)
def get_status_distribution(
    db: Annotated[Session, Depends(get_db)],
) -> CategoryDistributionResponse:
    rows = AnalyticsService(db).get_status_distribution()
    return _to_distribution_response(rows)


# ---------------------------------------------------------------------
# /district-distribution
# ---------------------------------------------------------------------


@router.get(
    "/district-distribution",
    response_model=CategoryDistributionResponse,
    summary="Cases grouped by District",
    description=(
        "Returns one row per District, with the count. No filter — "
        "this is a global distribution.\n\n"
        "**Example:**\n"
        "```\n"
        "GET /api/v1/dashboard/district-distribution\n"
        "```"
    ),
    responses=standard_error_responses(
        success_model=CategoryDistributionResponse,
        success_description="One row per District, with the count.",
        success_examples={
            "normal": examples.EXAMPLE_DISTRICT_NORMAL,
            "empty": examples.EXAMPLE_DISTRICT_EMPTY,
        },
        include_not_found=False,
    ),
    openapi_extra=code_samples(
        {
            "lang": "curl",
            "source": (
                "curl 'http://localhost:8000/api/v1/dashboard/"
                "district-distribution'"
            ),
        },
    ),
)
def get_district_distribution(
    db: Annotated[Session, Depends(get_db)],
) -> CategoryDistributionResponse:
    rows = AnalyticsService(db).get_district_distribution()
    return _to_distribution_response(rows)


# ---------------------------------------------------------------------
# /recent-cases
# ---------------------------------------------------------------------


@router.get(
    "/recent-cases",
    response_model=RecentCasesResponse,
    summary="Most recently registered cases",
    description=(
        "Returns the latest registered cases, paginated. The "
        "ordering is `CrimeRegisteredDate` desc, then "
        "`CaseMasterID` desc for stable ordering.\n\n"
        "**Pagination:**\n"
        "  * `page` (≥1, default 1) — 1-based page number.\n"
        "  * `page_size` (1..50, default 10) — items per page.\n\n"
        "**Example:**\n"
        "```\n"
        "GET /api/v1/dashboard/recent-cases\n"
        "```"
    ),
    responses=standard_error_responses(
        success_model=RecentCasesResponse,
        success_description=(
            "Most recent cases, ordered by registered date desc."
        ),
        success_examples={
            "normal": examples.EXAMPLE_RECENT_NORMAL,
            "empty": examples.EXAMPLE_RECENT_EMPTY,
        },
        include_not_found=False,
    ),
    openapi_extra=code_samples(
        {
            "lang": "curl",
            "source": (
                "curl 'http://localhost:8000/api/v1/dashboard/recent-cases'"
            ),
        },
        {
            "lang": "curl",
            "source": (
                "curl 'http://localhost:8000/api/v1/dashboard/recent-cases"
                "?page=2&page_size=5'"
            ),
        },
    ),
)
def get_recent_cases(
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[
        int, Query(ge=1, description="1-based page number")
    ] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=50, description="Items per page (1-50, default 10)"),
    ] = 10,
) -> RecentCasesResponse:
    cases, total = AnalyticsService(db).get_recent_cases(
        page=page, page_size=page_size
    )
    items = [CaseSummaryOut.model_validate(c) for c in cases]
    meta = calculate_pagination(page=page, page_size=page_size, total=total)
    log.info(
        "dashboard.recent_cases page=%s size=%s total=%s returned=%s",
        page,
        page_size,
        total,
        len(items),
    )
    return RecentCasesResponse(items=items, pagination=meta)


# ---------------------------------------------------------------------
# Local helpers
# ---------------------------------------------------------------------


def _to_distribution_response(rows) -> CategoryDistributionResponse:
    """Convert a list of :class:`CategoryCount` to the Pydantic envelope."""
    items = [
        CategoryCountOut(key=r.key, label=r.label, case_count=r.case_count)
        for r in rows
    ]
    return CategoryDistributionResponse(
        items=items,
        total=sum(r.case_count for r in rows),
    )


def _lookup_district(
    db: Session,
    *,
    name: str | None = None,
    district_id: int | None = None,
) -> DistrictRefOut | None:
    """Resolve a district name or id to a :class:`DistrictRefOut`.

    Used by the monthly-trends endpoint to echo the applied filter
    back to the caller. Returns ``None`` when the lookup fails —
    the caller will still get a valid 200 with 12 zero counts.
    """
    from sqlalchemy import func, select

    from backend.models.geography import District

    stmt = select(District.DistrictID, District.DistrictName)
    if district_id is not None:
        stmt = stmt.where(District.DistrictID == district_id)
    elif name is not None:
        stmt = stmt.where(func.lower(District.DistrictName) == name.strip().lower())
    else:
        return None
    row = db.execute(stmt).first()
    if row is None:
        return None
    return DistrictRefOut(district_id=row[0], district_name=row[1])
