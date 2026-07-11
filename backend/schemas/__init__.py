"""
Pydantic request/response schemas for the Saaransh API.

  - common    : pagination, sort, error envelope
  - case      : FIR (CaseMaster) and all related sub-collections
  - dashboard : analytics / dashboard aggregations (Phase 4)
"""
from backend.schemas.case import (
    AccusedOut,
    ActSectionOut,
    AssignedOfficerOut,
    CaseCategoryRef,
    CaseDetailOut,
    CaseListResponse,
    CaseStatusRef,
    CaseSummaryOut,
    ChargesheetOut,
    ComplainantOut,
    CourtRef,
    CrimeHeadRef,
    CrimeSubHeadRef,
    DistrictRef,
    EvidenceOut,
    GravityRef,
    PoliceStationRef,
    RecoveredItemOut,
    VictimOut,
)
from backend.schemas.common import (
    ErrorDetail,
    ErrorResponse,
    PaginatedResponse,
    PaginationMeta,
    PaginationParams,
    SortOrder,
    make_paginated_response,
)
from backend.schemas.dashboard import (
    CategoryCountOut,
    CategoryDistributionResponse,
    DashboardSummaryOut,
    DistrictRefOut,
    MonthlyTrendPoint,
    MonthlyTrendsResponse,
    RecentCasesResponse,
)

__all__ = [
    # common
    "ErrorDetail",
    "ErrorResponse",
    "PaginatedResponse",
    "PaginationMeta",
    "PaginationParams",
    "SortOrder",
    "make_paginated_response",
    # case references
    "CaseCategoryRef",
    "CaseStatusRef",
    "CourtRef",
    "CrimeHeadRef",
    "CrimeSubHeadRef",
    "DistrictRef",
    "GravityRef",
    "PoliceStationRef",
    # case sub-models
    "AccusedOut",
    "ActSectionOut",
    "AssignedOfficerOut",
    "ChargesheetOut",
    "ComplainantOut",
    "EvidenceOut",
    "RecoveredItemOut",
    "VictimOut",
    # case top-level
    "CaseDetailOut",
    "CaseListResponse",
    "CaseSummaryOut",
    # dashboard / analytics
    "CategoryCountOut",
    "CategoryDistributionResponse",
    "DashboardSummaryOut",
    "DistrictRefOut",
    "MonthlyTrendPoint",
    "MonthlyTrendsResponse",
    "RecentCasesResponse",
]
