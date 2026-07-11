"""
Service layer — business logic lives here.

The service layer is the only part of the codebase that talks to the
database. Services are intentionally FastAPI-independent so they can
be reused by:

  * HTTP routes (current — via :func:`backend.database.get_db`)
  * The Gemini AI provider (Phase 6+ — via the same constructor)
  * Background jobs and one-off scripts

Phase 6 adds two new collaborators that follow the same pattern:

  * :class:`SQLExecutor` (and :class:`SQLAlchemySQLExecutor`) —
    read-only SQL execution. The AI service layer depends on this
    interface, never on the concrete implementation.
  * :class:`AIQueryService` — thin facade used by the investigation
    service to run validated SQL and to expose the schema allowlist.

See :mod:`backend.services.base` for the contract every service
inherits. See :mod:`backend.services.schema_registry` for the
table / column allowlist the AI engine enforces.
"""
from backend.services.ai_query_service import AIQueryService
from backend.services.analytics_service import (
    AnalyticsService,
    CategoryCount,
    DistrictRef,
    MonthlyTrend,
    SummaryCounts,
)
from backend.services.base import BaseService
from backend.services.case_service import (
    ALLOWED_SORT_FIELDS,
    CaseFilters,
    CaseNotFoundError,
    CaseService,
    CaseSort,
)
from backend.services.schema_registry import (
    SCHEMA_TABLES,
    get_schema_registry,
    get_schema_summary,
    is_known_table,
    known_columns,
)
from backend.services.sql_executor import (
    ExecutionOperationError,
    ExecutionResult,
    FORBIDDEN_VERBS,
    READ_ONLY_VERBS,
    SQLAlchemySQLExecutor,
    SQLOperationError,
    SQLExecutor,
    UnsafeSQLOperation,
    assert_read_only,
    first_significant_token,
    normalise_value,
)

__all__ = [
    # base
    "BaseService",
    # case
    "ALLOWED_SORT_FIELDS",
    "CaseFilters",
    "CaseNotFoundError",
    "CaseService",
    "CaseSort",
    # analytics
    "AnalyticsService",
    "CategoryCount",
    "DistrictRef",
    "MonthlyTrend",
    "SummaryCounts",
    # AI collaboration (Phase 6)
    "AIQueryService",
    "SQLExecutor",
    "SQLAlchemySQLExecutor",
    "ExecutionResult",
    "ExecutionOperationError",
    "UnsafeSQLOperation",
    "SQLOperationError",
    "READ_ONLY_VERBS",
    "FORBIDDEN_VERBS",
    "assert_read_only",
    "first_significant_token",
    "normalise_value",
    # schema registry
    "SCHEMA_TABLES",
    "get_schema_registry",
    "get_schema_summary",
    "is_known_table",
    "known_columns",
]
