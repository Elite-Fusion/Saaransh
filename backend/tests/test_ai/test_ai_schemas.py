"""
Tests for the AI investigation schemas (Pydantic v2).

Every model is ``extra="forbid"`` and most fields are constrained.
The tests pin the contract so a refactor cannot accidentally loosen
the rules the route layer relies on.
"""
from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from backend.ai.schemas.ai import (
    ALLOWED_SQL_VERBS,
    CaseSearchOperation,
    DashboardAnalyticsOperation,
    EvidenceItem,
    ExplainCaseOperation,
    ExplanationBlock,
    GeneratedSQL,
    Intent,
    IntentClassification,
    InvestigationResponse,
    InvestigationSummaryOperation,
    OperationType,
    PlaceholderOperation,
    ValidatedSQL,
)


# ---------------------------------------------------------------------
# Intent enum
# ---------------------------------------------------------------------


class TestIntent:
    def test_six_values(self):
        assert {i.value for i in Intent} == {
            "case_search",
            "dashboard_analytics",
            "similar_cases",
            "investigation_summary",
            "explain_case",
            "unknown",
        }

    def test_value_is_string(self):
        assert Intent.CASE_SEARCH == "case_search"

    def test_allowed_sql_verbs(self):
        assert ALLOWED_SQL_VERBS == ("SELECT", "WITH")


# ---------------------------------------------------------------------
# IntentClassification
# ---------------------------------------------------------------------


class TestIntentClassification:
    def test_minimal(self):
        c = IntentClassification(
            intent=Intent.CASE_SEARCH,
            confidence=0.9,
            reasoning="Question uses a list trigger phrase.",
        )
        assert c.intent is Intent.CASE_SEARCH
        assert c.confidence == 0.9
        assert c.raw_response == ""

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            IntentClassification(
                intent=Intent.CASE_SEARCH,
                confidence=-0.1,
                reasoning="x",
            )
        with pytest.raises(ValidationError):
            IntentClassification(
                intent=Intent.CASE_SEARCH,
                confidence=1.1,
                reasoning="x",
            )

    def test_empty_reasoning_rejected(self):
        with pytest.raises(ValidationError):
            IntentClassification(
                intent=Intent.CASE_SEARCH,
                confidence=0.5,
                reasoning="",
            )

    def test_extra_rejected(self):
        with pytest.raises(ValidationError):
            IntentClassification(
                intent=Intent.CASE_SEARCH,
                confidence=0.5,
                reasoning="x",
                extra="no",
            )


# ---------------------------------------------------------------------
# GeneratedSQL
# ---------------------------------------------------------------------


class TestGeneratedSQL:
    def test_minimal(self):
        g = GeneratedSQL(sql="SELECT 1")
        assert g.sql == "SELECT 1"
        assert g.params == {}
        assert g.tables == []
        assert g.estimated_rows == "unknown"
        assert g.notes == ""

    def test_full(self):
        g = GeneratedSQL(
            sql="SELECT * FROM CaseMaster WHERE CaseMasterID = :id",
            params={":id": 12},
            tables=["CaseMaster"],
            estimated_rows="low",
            notes="indexed by PK",
        )
        assert g.params[":id"] == 12
        assert g.estimated_rows == "low"

    def test_estimated_rows_literal(self):
        with pytest.raises(ValidationError):
            GeneratedSQL(sql="SELECT 1", estimated_rows="lots")  # type: ignore[arg-type]

    def test_extra_rejected(self):
        with pytest.raises(ValidationError):
            GeneratedSQL(sql="SELECT 1", evil=True)


class TestValidatedSQL:
    def test_minimal(self):
        v = ValidatedSQL(sql="SELECT 1")
        assert v.sql == "SELECT 1"
        assert v.tables == []
        assert v.estimated_rows == "unknown"


# ---------------------------------------------------------------------
# EvidenceItem and ExplanationBlock
# ---------------------------------------------------------------------


class TestEvidenceItem:
    def test_minimal(self):
        e = EvidenceItem(label="row")
        assert e.case_id is None
        assert e.fir_number is None
        assert e.label == "row"

    def test_full(self):
        e = EvidenceItem(case_id=12, fir_number="1044", label="theft")
        assert e.case_id == 12
        assert e.fir_number == "1044"

    def test_label_required(self):
        with pytest.raises(ValidationError):
            EvidenceItem()  # type: ignore[call-arg]

    def test_extra_rejected(self):
        with pytest.raises(ValidationError):
            EvidenceItem(label="x", extra=True)


class TestExplanationBlock:
    def test_minimal(self):
        b = ExplanationBlock(summary="x", why="y")
        assert b.confidence == "medium"
        assert b.confidence_score == 0.5
        assert b.evidence == []
        assert b.caveats == []

    def test_confidence_literal(self):
        with pytest.raises(ValidationError):
            ExplanationBlock(summary="x", why="y", confidence="maybe")  # type: ignore[arg-type]

    def test_confidence_score_bounds(self):
        with pytest.raises(ValidationError):
            ExplanationBlock(summary="x", why="y", confidence_score=2.0)


# ---------------------------------------------------------------------
# InvestigationResponse
# ---------------------------------------------------------------------


class TestInvestigationResponse:
    def _minimal(self, **kwargs: Any) -> dict[str, Any]:
        base: dict[str, Any] = {
            "request_id": "req-1",
            "intent": Intent.CASE_SEARCH,
            "operation": OperationType.SERVICE,
            "reasoning": "because",
            "executed_operation": "CaseService.list_cases",
        }
        base.update(kwargs)
        return base

    def test_minimal(self):
        r = InvestigationResponse(**self._minimal())
        assert r.request_id == "req-1"
        assert r.confidence == 0.5
        assert r.assumptions == []
        assert r.supporting_evidence == []
        assert r.explanation is None
        assert r.raw_sql is None
        assert r.placeholder is None

    def test_sql_payload(self):
        r = InvestigationResponse(
            **self._minimal(
                operation=OperationType.SQL,
                raw_sql="SELECT 1",
                raw_params={},
                row_count=5,
                columns=["x"],
            )
        )
        assert r.raw_sql == "SELECT 1"
        assert r.row_count == 5
        assert r.columns == ["x"]

    def test_placeholder_payload(self):
        r = InvestigationResponse(
            **self._minimal(
                intent=Intent.SIMILAR_CASES,
                operation=OperationType.PLACEHOLDER,
                placeholder={"feature": "similar_cases"},
            )
        )
        assert r.placeholder == {"feature": "similar_cases"}

    def test_extra_rejected(self):
        with pytest.raises(ValidationError):
            InvestigationResponse(**self._minimal(sneaky="value"))


# ---------------------------------------------------------------------
# Operation descriptors
# ---------------------------------------------------------------------


class TestOperationDescriptors:
    def test_case_search_defaults(self):
        op = CaseSearchOperation()
        assert op.page == 1
        assert op.page_size == 20
        assert op.sort_field == "crime_registered_date"
        assert op.sort_order == "desc"

    def test_case_search_page_bounds(self):
        with pytest.raises(ValidationError):
            CaseSearchOperation(page=0)
        with pytest.raises(ValidationError):
            CaseSearchOperation(page_size=0)

    def test_dashboard_metrics(self):
        op = DashboardAnalyticsOperation(metric="monthly_trends", year=2024)
        assert op.metric == "monthly_trends"
        assert op.year == 2024
        with pytest.raises(ValidationError):
            DashboardAnalyticsOperation(year=1800)

    def test_explain_case_requires_id(self):
        with pytest.raises(ValidationError):
            ExplainCaseOperation()  # type: ignore[call-arg]
        op = ExplainCaseOperation(case_id=12)
        assert op.case_id == 12

    def test_investigation_summary(self):
        op = InvestigationSummaryOperation(case_id=1, similar_case_ids=[2, 3])
        assert op.similar_case_ids == [2, 3]

    def test_placeholder(self):
        op = PlaceholderOperation()
        assert op.feature == "similar_cases"
        op2 = PlaceholderOperation(case_id=7)
        assert op2.case_id == 7
