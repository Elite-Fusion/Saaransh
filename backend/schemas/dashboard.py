"""
Pydantic schemas — dashboard / analytics response models.

  - :class:`DashboardSummaryOut`        : the 6 headline numbers
  - :class:`MonthlyTrendPoint`          : one month bucket
  - :class:`MonthlyTrendsResponse`      : 12 months for a year + district filter echo
  - :class:`CategoryCountOut`           : one row in a distribution
  - :class:`CategoryDistributionResponse` : {items: [...], total: int}
  - :class:`RecentCasesResponse`        : {items: [...], pagination: ...}
  - :class:`DistrictRefOut`             : tiny reference used in trend responses

All field names follow the snake_case public API convention.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from backend.schemas.case import CaseSummaryOut
from backend.schemas.common import PaginationMeta

# ---------------------------------------------------------------------
# Tiny shared models
# ---------------------------------------------------------------------


class DistrictRefOut(BaseModel):
    """Echoed in monthly-trends so the caller sees which district
    filter was applied (or null when unfiltered)."""

    district_id: int
    district_name: str


# ---------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------


class DashboardSummaryOut(BaseModel):
    """The six headline numbers shown on the dashboard overview tile.

    ``convictions`` and ``acquittals`` are always 0 in the current
    schema — verdict data is not yet tracked. The fields exist in
    the contract so the API surface stays stable for the Gemini AI
    provider and the React UI; a future phase will populate them
    once a verdict table is added.
    """

    total_cases: int = Field(..., ge=0, description="Total FIRs registered.")
    open_cases: int = Field(
        ...,
        ge=0,
        description="Cases currently in 'Open' status.",
    )
    closed_cases: int = Field(
        ...,
        ge=0,
        description="Cases in 'Closed' status.",
    )
    charge_sheet_filed: int = Field(
        ...,
        ge=0,
        description="Cases in 'Charge Sheeted' status (a chargesheet has been filed).",
    )
    convictions: int = Field(
        ...,
        ge=0,
        description=(
            "Always 0 in the current schema — verdict data is not yet "
            "tracked. Will be populated in a future phase."
        ),
    )
    acquittals: int = Field(
        ...,
        ge=0,
        description=(
            "Always 0 in the current schema — verdict data is not yet "
            "tracked. Will be populated in a future phase."
        ),
    )


# ---------------------------------------------------------------------
# Monthly trends
# ---------------------------------------------------------------------


class MonthlyTrendPoint(BaseModel):
    year: int = Field(..., ge=1900, le=2200)
    month: int = Field(..., ge=1, le=12, description="1=Jan, 12=Dec")
    month_label: str = Field(..., description="Three-letter month, e.g. 'Jan'")
    case_count: int = Field(..., ge=0)


class MonthlyTrendsResponse(BaseModel):
    year: int
    district: DistrictRefOut | None = Field(
        default=None,
        description="Echoes the district filter; null when unfiltered.",
    )
    items: list[MonthlyTrendPoint] = Field(
        default_factory=list,
        description=(
            "Always 12 entries — Jan..Dec. Months with no cases "
            "appear with `case_count: 0`."
        ),
    )


# ---------------------------------------------------------------------
# Distributions (status, crime head, district)
# ---------------------------------------------------------------------


class CategoryCountOut(BaseModel):
    key: int | None = Field(
        default=None,
        description="Lookup-table id; null when the FK is null in the DB.",
    )
    label: str = Field(..., description="Human-readable category name.")
    case_count: int = Field(..., ge=0)


class CategoryDistributionResponse(BaseModel):
    items: list[CategoryCountOut] = Field(default_factory=list)
    total: int = Field(..., ge=0, description="Sum of every case_count.")


# ---------------------------------------------------------------------
# Recent cases — reuses the case summary shape + pagination meta
# ---------------------------------------------------------------------


class RecentCasesResponse(BaseModel):
    items: list[CaseSummaryOut] = Field(default_factory=list)
    pagination: PaginationMeta
