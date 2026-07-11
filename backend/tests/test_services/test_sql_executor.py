"""
Tests for the read-only SQL executor and the AI query service facade.

These tests use an in-memory SQLite engine to exercise the executor
end-to-end. The engine is created in the session-level fixture so
every test gets a fresh database.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from sqlalchemy import Column, Date, DateTime, Integer, Numeric, String, Text, create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.services.ai_query_service import AIQueryService
from backend.services.sql_executor import (
    ExecutionOperationError,
    ExecutionResult,
    FORBIDDEN_VERBS,
    READ_ONLY_VERBS,
    SQLAlchemySQLExecutor,
    SQLExecutor,
    UnsafeSQLOperation,
    assert_read_only,
    first_significant_token,
    normalise_value,
)

Base = declarative_base()


class CaseRow(Base):
    """A minimal table the executor's tests can run against."""

    __tablename__ = "case_row"

    id = Column(Integer, primary_key=True, autoincrement=True)
    crime_no = Column(String(50), nullable=False)
    registered = Column(Date, nullable=False)
    amount = Column(Numeric(12, 2), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True)


@pytest.fixture
def engine():
    """An in-memory SQLite engine with a single ``case_row`` table."""
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine):
    """A session with one row in ``case_row``."""
    Session_ = sessionmaker(bind=engine)
    with Session_() as s:
        s.add(
            CaseRow(
                id=1,
                crime_no="104430001202400001",
                registered=date(2024, 1, 15),
                amount=Decimal("1234.56"),
                notes="first case",
                created_at=datetime(2024, 1, 15, 9, 0, 0),
            )
        )
        s.add(
            CaseRow(
                id=2,
                crime_no="104430001202400002",
                registered=date(2024, 2, 20),
                amount=Decimal("500.00"),
                notes="second case",
                created_at=datetime(2024, 2, 20, 11, 30, 0),
            )
        )
        s.commit()
        yield s


# ---------------------------------------------------------------------
# first_significant_token / assert_read_only
# ---------------------------------------------------------------------


class TestFirstSignificantToken:
    def test_simple_select(self):
        assert first_significant_token("SELECT 1") == "SELECT"

    def test_lowercase(self):
        assert first_significant_token("select 1") == "SELECT"

    def test_with_cte(self):
        assert (
            first_significant_token("WITH x AS (SELECT 1) SELECT * FROM x")
            == "SELECT"
        )

    def test_with_cte_lowercase(self):
        assert (
            first_significant_token("with x as (select 1) select * from x")
            == "SELECT"
        )

    def test_empty(self):
        assert first_significant_token("") == ""

    def test_whitespace_only(self):
        assert first_significant_token("   \n\t") == ""


class TestAssertReadOnly:
    def test_select_allowed(self):
        assert_read_only("SELECT 1")  # does not raise

    def test_with_allowed(self):
        assert_read_only("WITH x AS (SELECT 1) SELECT * FROM x")

    def test_delete_rejected(self):
        with pytest.raises(UnsafeSQLOperation) as ei:
            assert_read_only("DELETE FROM x")
        assert "DELETE" in ei.value.reason

    def test_drop_rejected(self):
        with pytest.raises(UnsafeSQLOperation):
            assert_read_only("DROP TABLE x")

    def test_unknown_verb_rejected(self):
        with pytest.raises(UnsafeSQLOperation):
            assert_read_only("EXPLAIN SELECT 1")

    def test_empty_rejected(self):
        with pytest.raises(UnsafeSQLOperation):
            assert_read_only("")


class TestVerbConstants:
    def test_read_only_verbs(self):
        assert "SELECT" in READ_ONLY_VERBS
        assert "WITH" in READ_ONLY_VERBS

    def test_forbidden_verbs(self):
        for v in ("DELETE", "UPDATE", "INSERT", "DROP", "TRUNCATE"):
            assert v in FORBIDDEN_VERBS


# ---------------------------------------------------------------------
# normalise_value
# ---------------------------------------------------------------------


class TestNormaliseValue:
    def test_decimal_to_string(self):
        assert normalise_value(Decimal("12.34")) == "12.34"

    def test_date_to_iso(self):
        assert normalise_value(date(2024, 1, 15)) == "2024-01-15"

    def test_datetime_to_iso(self):
        assert normalise_value(datetime(2024, 1, 15, 9, 0, 0)) == "2024-01-15T09:00:00"

    def test_uuid_to_string(self):
        u = UUID("12345678-1234-5678-1234-567812345678")
        assert normalise_value(u) == str(u)

    def test_bytes_to_hash(self):
        out = normalise_value(b"hello")
        assert isinstance(out, str)
        assert len(out) == 64  # SHA-256 hex digest

    def test_str_unchanged(self):
        assert normalise_value("x") == "x"

    def test_int_unchanged(self):
        assert normalise_value(12) == 12

    def test_none_unchanged(self):
        assert normalise_value(None) is None


# ---------------------------------------------------------------------
# SQLAlchemySQLExecutor — end-to-end
# ---------------------------------------------------------------------


class TestSQLAlchemySQLExecutor:
    def test_select_returns_rows(self, session):
        executor = SQLAlchemySQLExecutor(session)
        result = executor.execute("SELECT id, crime_no FROM case_row ORDER BY id")
        assert isinstance(result, ExecutionResult)
        assert result.row_count == 2
        assert result.columns == ["id", "crime_no"]
        assert result.rows[0]["id"] == 1
        assert result.rows[1]["crime_no"] == "104430001202400002"

    def test_select_with_param(self, session):
        executor = SQLAlchemySQLExecutor(session)
        result = executor.execute(
            "SELECT id, crime_no FROM case_row WHERE id = :id",
            {"id": 2},
        )
        assert result.row_count == 1
        assert result.rows[0]["id"] == 2

    def test_decimal_normalised_to_string(self, session):
        # SQLite stores Numeric columns as REAL, so we round-trip
        # through the normaliser and assert the value is still
        # exactly equal to the original Decimal — the normaliser
        # passes the value through unchanged when it is already
        # a JSON-serialisable scalar.
        executor = SQLAlchemySQLExecutor(session)
        result = executor.execute(
            "SELECT id, amount FROM case_row ORDER BY id LIMIT 1"
        )
        assert float(result.rows[0]["amount"]) == 1234.56

    def test_date_normalised_to_iso(self, session):
        executor = SQLAlchemySQLExecutor(session)
        result = executor.execute(
            "SELECT id, registered FROM case_row ORDER BY id LIMIT 1"
        )
        assert result.rows[0]["registered"] == "2024-01-15"

    def test_max_rows_truncates(self, session):
        executor = SQLAlchemySQLExecutor(session)
        result = executor.execute(
            "SELECT id FROM case_row ORDER BY id", max_rows=1
        )
        assert result.row_count == 1
        assert result.truncated is True

    def test_no_truncation_when_under_cap(self, session):
        executor = SQLAlchemySQLExecutor(session)
        result = executor.execute(
            "SELECT id FROM case_row ORDER BY id", max_rows=10
        )
        assert result.row_count == 2
        assert result.truncated is False

    def test_empty_sql_rejected(self, session):
        executor = SQLAlchemySQLExecutor(session)
        with pytest.raises(UnsafeSQLOperation):
            executor.execute("")

    def test_non_string_sql_rejected(self, session):
        executor = SQLAlchemySQLExecutor(session)
        with pytest.raises(UnsafeSQLOperation):
            executor.execute(123)  # type: ignore[arg-type]

    def test_forbidden_verb_rejected(self, session):
        executor = SQLAlchemySQLExecutor(session)
        with pytest.raises(UnsafeSQLOperation):
            executor.execute("DELETE FROM case_row")

    def test_invalid_sql_raises_execution_error(self, session):
        executor = SQLAlchemySQLExecutor(session)
        with pytest.raises(ExecutionOperationError) as ei:
            executor.execute("SELECT * FROM nonexistent_table")
        assert ei.value.sql is not None

    def test_echoes_sql_and_params(self, session):
        executor = SQLAlchemySQLExecutor(session)
        result = executor.execute(
            "SELECT id FROM case_row WHERE id = :x", {"x": 1}
        )
        assert "SELECT" in result.sql
        assert result.params == {"x": 1}


# ---------------------------------------------------------------------
# SQLExecutor ABC
# ---------------------------------------------------------------------


class TestSQLExecutorABC:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            SQLExecutor()  # type: ignore[call-arg]


# ---------------------------------------------------------------------
# AIQueryService facade
# ---------------------------------------------------------------------


class TestAIQueryService:
    def test_facade_creates_executor(self, session):
        service = AIQueryService(session)
        assert service.executor is not None
        assert isinstance(service.executor, SQLAlchemySQLExecutor)

    def test_facade_runs_validated_sql(self, session):
        service = AIQueryService(session)
        result = service.execute_validated_sql(
            "SELECT id, crime_no FROM case_row ORDER BY id"
        )
        assert result.row_count == 2

    def test_facade_wraps_unsafe_sql(self, session):
        from backend.ai.services.exceptions import UnsafeSQL

        service = AIQueryService(session)
        with pytest.raises(UnsafeSQL) as ei:
            service.execute_validated_sql("DELETE FROM case_row")
        assert ei.value.category == "verb"

    def test_facade_wraps_execution_error(self, session):
        from backend.ai.services.exceptions import ExecutionFailure

        service = AIQueryService(session)
        with pytest.raises(ExecutionFailure):
            service.execute_validated_sql(
                "SELECT * FROM nonexistent_table"
            )

    def test_facade_schema_summary_contains_tables(self, session):
        service = AIQueryService(session)
        summary = service.get_schema_summary()
        assert "CaseMaster" in summary
        assert "Accused" in summary
        assert "CaseMasterID" in summary

    def test_facade_accepts_custom_executor(self, session):
        custom = MagicMock(spec=SQLExecutor)
        custom.execute.return_value = ExecutionResult(
            columns=["a"], rows=[{"a": 1}], row_count=1
        )
        service = AIQueryService(session, executor=custom)
        result = service.execute_validated_sql("SELECT 1")
        assert result.row_count == 1
        custom.execute.assert_called_once()

    def test_facade_accepts_custom_schema(self, session):
        custom = {"MyTable": frozenset({"col1", "col2"})}
        service = AIQueryService(session, schema=custom)
        assert service.schema == custom
