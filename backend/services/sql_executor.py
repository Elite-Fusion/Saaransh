"""
Read-only SQL executor — the only place in the Phase 6 codebase that
turns validated SQL into rows.

The :class:`SQLExecutor` is a thin wrapper over
``session.execute(text(sql), params)`` with two layers of defence:

  1. **Allowlist at the entry point.** Before touching the session, the
     executor re-validates the SQL against a small verb allowlist. The
     :class:`~backend.ai.services.sql_validation_service.SQLValidationService`
     should already have rejected anything outside it, but a second
     check here means a misuse of the executor from a future caller
     still cannot mutate the database.
  2. **No string concatenation.** All user-supplied values are bound
     parameters, never interpolated. The executor only ever calls
     ``session.execute(text(sql), params)``.

The executor returns rows as a ``list[dict]`` plus a ``columns`` list.
Datetimes are ISO-formatted so the JSON serialisation in the route
layer (Phase 7+) works without custom encoders.

Why this lives in :mod:`backend.services`?

The Phase 5 independence test forbids ``sqlalchemy`` imports under
``backend/ai/**``. The AI service layer takes a
:class:`SQLExecutor` (the abstract base defined here) as a constructor
argument and never imports the concrete implementation directly. Tests
can swap in the in-memory SQLite variant from
:mod:`backend.tests.conftest`.

The executor raises its own :class:`UnsafeSQLOperation` /
:class:`ExecutionOperationError` subclasses of :class:`Exception`. The
AI investigation service catches these and re-wraps them into the
AI-domain :class:`~backend.ai.services.exceptions.UnsafeSQL` and
:class:`~backend.ai.services.exceptions.ExecutionFailure`. That
direction-of-imports is deliberate — the AI layer depends on the
service layer, never the other way around.
"""
from __future__ import annotations

import hashlib
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Mapping, Sequence
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


# Defence-in-depth: a copy of the allowlist. The Phase 6 validator is
# the primary gate; this list is the second. They MUST stay in sync.
READ_ONLY_VERBS: frozenset[str] = frozenset({"SELECT", "WITH"})
FORBIDDEN_VERBS: frozenset[str] = frozenset(
    {
        "DELETE",
        "UPDATE",
        "INSERT",
        "ALTER",
        "DROP",
        "TRUNCATE",
        "CREATE",
        "EXEC",
        "CALL",
        "MERGE",
        "COPY",
        "GRANT",
        "REVOKE",
    }
)

_LEADING_WITH_RE = re.compile(r"^\s*WITH\b", re.IGNORECASE)
_FIRST_WORD_RE = re.compile(r"^\s*([A-Za-z_]+)")
_WORD_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b")


class SQLOperationError(Exception):
    """Base class for every error raised by the executor layer.

    The AI investigation service catches this and re-wraps into the
    AI-domain :class:`~backend.ai.services.exceptions.InvestigationError`
    hierarchy. Other callers (scripts, tests) can catch
    :class:`SQLOperationError` directly.
    """


class UnsafeSQLOperation(SQLOperationError):
    """The verb allowlist rejected the statement.

    Should never fire if the SQL validator ran first — this is
    defence in depth. The message is safe to surface to the route
    layer.
    """

    def __init__(self, reason: str, *, sql: str | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.sql = sql


class ExecutionOperationError(SQLOperationError):
    """A :class:`SQLAlchemyError` escaped the executor.

    The AI service layer re-wraps this as
    :class:`~backend.ai.services.exceptions.ExecutionFailure`.
    """

    def __init__(
        self,
        message: str,
        *,
        original: Exception | None = None,
        sql: str | None = None,
    ) -> None:
        super().__init__(message)
        self.original = original
        self.sql = sql


_SQL_VERBS = frozenset(
    {
        "SELECT",
        "WITH",
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "TRUNCATE",
        "ALTER",
        "CREATE",
        "GRANT",
        "REVOKE",
        "MERGE",
        "CALL",
        "COPY",
        "EXEC",
        "EXPLAIN",
        "SHOW",
    }
)


def first_significant_token(sql: str) -> str:
    """Return the first significant verb in ``sql``.

    Strips a leading ``WITH`` so ``WITH x AS (...) SELECT ...`` is
    correctly identified as a read query. Returns the empty string
    when no verb token is found.
    """
    cleaned = _LEADING_WITH_RE.sub("", sql, count=1).lstrip()
    for match in _WORD_RE.finditer(cleaned):
        token = match.group(1).upper()
        if token in _SQL_VERBS:
            return token
    return ""


def assert_read_only(sql: str) -> None:
    """Raise :class:`UnsafeSQLOperation` if ``sql`` is not a read query.

    Local re-implementation of the same allowlist check the
    :class:`SQLValidationService` performs. We keep a copy here so
    the executor has no upward import into ``backend.ai``.
    """
    verb = first_significant_token(sql)
    if not verb:
        raise UnsafeSQLOperation("SQL has no recognisable leading verb.", sql=sql)
    if verb in FORBIDDEN_VERBS:
        raise UnsafeSQLOperation(
            f"SQL uses forbidden verb {verb!r}. "
            f"Only {sorted(READ_ONLY_VERBS)} are allowed.",
            sql=sql,
        )
    if verb not in READ_ONLY_VERBS:
        raise UnsafeSQLOperation(
            f"SQL uses unsupported verb {verb!r}. "
            f"Only {sorted(READ_ONLY_VERBS)} are allowed.",
            sql=sql,
        )


def normalise_value(value: Any) -> Any:
    """Convert non-JSON-serialisable values to JSON-friendly forms.

    The route layer (Phase 7+) will serialise the executor's output
    verbatim. ``Decimal`` and ``UUID`` are not JSON-native, so we
    convert them here rather than at serialisation time. The
    conversion is intentionally loss-free (``Decimal`` -> ``str``,
    ``UUID`` -> ``str``) so the LLM can still read the values.
    """
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (bytes, bytearray)):
        return hashlib.sha256(bytes(value)).hexdigest()
    return value


@dataclass(frozen=True)
class ExecutionResult:
    """The result of a single read-only query.

    Attributes:
        columns: The column names in the order SQLAlchemy returned them.
        rows: One dict per row, in the same column order. Non-JSON
            values (``Decimal``, ``UUID``, ``datetime``) are normalised
            to strings so the result is ready for the LLM prompt.
        row_count: ``len(rows)`` — cached for the route layer.
        sql: The SQL that was actually executed (echoed for the
            audit log).
        params: The bound parameters that were actually used.
        truncated: ``True`` if the executor cut the result set short
            because ``max_rows`` was hit. ``False`` for unlimited
            queries.
    """

    columns: list[str] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    row_count: int = 0
    sql: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    truncated: bool = False


class SQLExecutor(ABC):
    """Abstract base for a read-only SQL executor.

    The AI service layer depends on this interface, never on a concrete
    implementation. A future Phase 7 may add a separate "explain" or
    "metrics" executor that runs the same query through a different
    channel; the interface keeps the option open.
    """

    @abstractmethod
    def execute(
        self,
        sql: str,
        params: Mapping[str, Any] | None = None,
        *,
        max_rows: int | None = None,
    ) -> ExecutionResult:
        """Run ``sql`` with bound ``params`` and return the rows.

        Args:
            sql: A single ``SELECT`` (or ``WITH ... SELECT``) statement
                that has already passed validation. The executor still
                re-checks the verb allowlist — defence in depth.
            params: Named bind parameters (``":district_id": 12``).
                ``None`` and empty mappings are equivalent.
            max_rows: If given, the executor stops after collecting
                this many rows. Useful when the SQL has no ``LIMIT``
                but the caller wants to bound memory.

        Returns:
            An :class:`ExecutionResult` with the rows, columns, and
            echoed ``sql`` / ``params``.

        Raises:
            UnsafeSQLOperation: The verb allowlist rejected the
                statement (should never happen if the validator ran
                first).
            ExecutionOperationError: The database raised a
                :class:`SQLAlchemyError`.
        """
        raise NotImplementedError


class SQLAlchemySQLExecutor(SQLExecutor):
    """Concrete :class:`SQLExecutor` that runs through SQLAlchemy."""

    # Hard cap to prevent the LLM from streaming the entire CaseMaster
    # table into the prompt. Phase 6's validator already requires
    # ``LIMIT`` for SELECTs, but the executor enforces a second cap.
    DEFAULT_MAX_ROWS: int = 1000

    def __init__(
        self,
        session: Session,
        *,
        logger: logging.Logger | None = None,
        max_rows: int = DEFAULT_MAX_ROWS,
    ) -> None:
        self._session = session
        self._max_rows = int(max_rows)
        self._logger = logger or logging.getLogger(
            "backend.services.sql_executor"
        )

    def execute(
        self,
        sql: str,
        params: Mapping[str, Any] | None = None,
        *,
        max_rows: int | None = None,
    ) -> ExecutionResult:
        """Run ``sql`` and return rows as ``list[dict]``."""
        if not isinstance(sql, str) or not sql.strip():
            raise UnsafeSQLOperation("SQL is empty or not a string.", sql=sql)
        bound = dict(params or {})

        # Defence-in-depth: re-validate the verb allowlist before any
        # database call. The validator is the primary gate, but a
        # future caller of this executor may have skipped it.
        assert_read_only(sql)

        cap = int(max_rows) if max_rows is not None else self._max_rows

        self._logger.info(
            "sql_executor_run sql_chars=%d params=%d max_rows=%s",
            len(sql),
            len(bound),
            cap if cap is not None else "unbounded",
        )

        try:
            result = self._session.execute(text(sql), bound)
        except SQLAlchemyError as exc:
            self._logger.warning(
                "sql_executor_failure error_type=%s error=%s",
                type(exc).__name__,
                str(exc)[:200],
            )
            raise ExecutionOperationError(
                f"Database error: {type(exc).__name__}: {exc}",
                original=exc,
                sql=sql,
            ) from exc

        # ``mappings()`` is the SQLAlchemy 2.x row-mapper. Converting
        # through ``dict(...)`` consumes the row; do it eagerly.
        columns: list[str] = list(result.keys())
        raw_rows: Sequence[Mapping[str, Any]] = result.mappings().all()
        truncated = cap is not None and len(raw_rows) > cap
        if truncated:
            raw_rows = raw_rows[:cap]

        rows: list[dict[str, Any]] = [
            {col: normalise_value(row.get(col)) for col in columns}
            for row in raw_rows
        ]

        return ExecutionResult(
            columns=columns,
            rows=rows,
            row_count=len(rows),
            sql=sql,
            params=bound,
            truncated=truncated,
        )


__all__ = [
    "ExecutionResult",
    "ExecutionOperationError",
    "FORBIDDEN_VERBS",
    "READ_ONLY_VERBS",
    "SQLAlchemySQLExecutor",
    "SQLOperationError",
    "SQLExecutor",
    "UnsafeSQLOperation",
    "assert_read_only",
    "first_significant_token",
    "normalise_value",
]
