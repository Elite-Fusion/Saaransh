"""
AIQueryService — the AI-facing facade over the read-only SQL executor.

The AI investigation engine in :mod:`backend.ai.services` must not
import ``sqlalchemy`` or ``backend.models`` (Phase 5 independence
rule). It therefore talks to the database through this thin facade:

  * :meth:`execute_validated_sql` — runs a :class:`GeneratedSQL`
    through the executor and returns the result. Wraps executor
    errors into the AI-domain exception hierarchy.
  * :meth:`get_schema_summary` — exposes the schema allowlist as
    Markdown for the ``{{SCHEMA_SUMMARY}}`` placeholder in
    :file:`backend/ai/prompts/sql_prompt.md`.

The service takes a :class:`SQLExecutor` and a schema registry in its
constructor — neither is bound to a global — so tests can substitute
an in-memory SQLite executor and a stub registry without touching
the rest of the codebase.
"""
from __future__ import annotations

import logging
from typing import Any, Mapping

from sqlalchemy.orm import Session

from backend.services.schema_registry import (
    get_schema_registry,
    get_schema_summary,
)
from backend.services.sql_executor import (
    ExecutionOperationError,
    ExecutionResult,
    SQLAlchemySQLExecutor,
    SQLExecutor,
    UnsafeSQLOperation,
)


class AIQueryService:
    """AI-facing facade over the read-only SQL executor.

    Args:
        session: A SQLAlchemy ``Session``. Typically the request-scoped
            session obtained from :func:`backend.database.get_db`.
        executor: Optional :class:`SQLExecutor` override. Defaults to
            :class:`SQLAlchemySQLExecutor` built around ``session``.
        schema: A mapping of ``table -> frozenset[column]``. Defaults
            to :data:`backend.services.schema_registry.SCHEMA_TABLES`.
            Tests can pass a smaller mapping.
        logger: Optional :class:`logging.Logger`. Defaults to a
            module-level logger.
    """

    def __init__(
        self,
        session: Session,
        *,
        executor: SQLExecutor | None = None,
        schema: Mapping[str, Any] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._session = session
        self._executor = executor or SQLAlchemySQLExecutor(session)
        self._schema = schema if schema is not None else get_schema_registry()
        self._logger = logger or logging.getLogger("backend.services.ai_query_service")

    # ------------------------------------------------------------------
    # Public surface
    # ------------------------------------------------------------------

    def execute_validated_sql(
        self,
        sql: str,
        params: Mapping[str, Any] | None = None,
        *,
        max_rows: int | None = None,
    ) -> ExecutionResult:
        """Run a validated ``SELECT`` and return its rows.

        The AI service layer has already passed the statement through
        :class:`~backend.ai.services.sql_validation_service.SQLValidationService`,
        so this call is expected to succeed. The executor re-checks
        the verb allowlist as defence in depth.

        Args:
            sql: A single, validated ``SELECT`` statement.
            params: Named bind parameters.
            max_rows: Optional row cap; the executor's default applies
                when ``None``.

        Returns:
            An :class:`ExecutionResult` with rows as ``list[dict]``.

        Raises:
            :class:`backend.ai.services.exceptions.UnsafeSQL`:
                The verb allowlist rejected the statement. This is a
                re-wrapping of :class:`UnsafeSQLOperation`.
            :class:`backend.ai.services.exceptions.ExecutionFailure`:
                The database raised while running the query. This is
                a re-wrapping of :class:`ExecutionOperationError`.
        """
        # Lazy imports — keeps the AI service layer unaware of the
        # service-layer exception types until the failure happens.
        from backend.ai.services.exceptions import (
            ExecutionFailure,
            UnsafeSQL,
        )

        try:
            return self._executor.execute(sql, params, max_rows=max_rows)
        except UnsafeSQLOperation as exc:
            # Mirror the executor's reason into the AI-domain
            # exception so the route layer only has to know about
            # one hierarchy.
            raise UnsafeSQL(exc.reason, sql=exc.sql, category="verb") from exc
        except ExecutionOperationError as exc:
            raise ExecutionFailure(
                str(exc),
                original=exc.original,
                sql=exc.sql,
            ) from exc

    def get_schema_summary(self) -> str:
        """Return the schema allowlist as a Markdown table.

        The text is injected into the ``{{SCHEMA_SUMMARY}}`` placeholder
        of :file:`backend/ai/prompts/sql_prompt.md` so the LLM sees the
        same allowlist the validator enforces.
        """
        # Use the same helper the registry module exposes.
        return get_schema_summary()

    @property
    def schema(self) -> Mapping[str, Any]:
        """The schema allowlist (table -> frozenset[column])."""
        return self._schema

    @property
    def executor(self) -> SQLExecutor:
        """The underlying :class:`SQLExecutor`."""
        return self._executor

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"AIQueryService(executor={type(self._executor).__name__}, "
            f"tables={len(self._schema)})"
        )


__all__ = ["AIQueryService"]
