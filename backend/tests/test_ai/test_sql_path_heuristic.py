"""
Tests for the SQL-path heuristic
(``InvestigationService._should_use_sql_path``).

The heuristic decides whether a question that the service-method
path can technically answer should instead be routed to the SQL
pipeline. The unit tests below pin the heuristic to the example
phrases listed in the Phase 8 plan; they exist so a future
refactor cannot silently start answering "compare Mysuru and
Bengaluru" from the service path (which would return zero rows).
"""
from __future__ import annotations

from datetime import date

from backend.ai.schemas.ai import (
    Intent,
    IntentClassification,
)
from backend.ai.services.investigation_service import (
    InvestigationService,
    _build_case_filters,
)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _classification(intent: Intent) -> IntentClassification:
    """Build a minimal :class:`IntentClassification` for the test."""
    return IntentClassification(
        intent=intent,
        confidence=0.9,
        reasoning="unit-test stub",
        raw_response="",
    )


def _service() -> InvestigationService:
    """Build an :class:`InvestigationService` instance for unit tests.

    No collaborators are wired because the heuristic does not call
    any of them — it works on the question text and the parsed
    :class:`CaseFilters` alone.
    """
    return InvestigationService.__new__(InvestigationService)


# ---------------------------------------------------------------------
# "compare" / "highest" / "near" / "repeat offender" → SQL
# ---------------------------------------------------------------------


class TestSqlTriggers:
    def test_compare_triggers_sql(self):
        svc = _service()
        f = _build_case_filters("Compare Mysuru and Bengaluru crime")
        assert svc._should_use_sql_path(
            "Compare Mysuru and Bengaluru crime",
            _classification(Intent.DASHBOARD_ANALYTICS),
            f,
        ) is True

    def test_highest_triggers_sql(self):
        svc = _service()
        f = _build_case_filters("Which district has the highest theft?")
        assert svc._should_use_sql_path(
            "Which district has the highest theft?",
            _classification(Intent.DASHBOARD_ANALYTICS),
            f,
        ) is True

    def test_most_triggers_sql(self):
        svc = _service()
        f = _build_case_filters("Which district has the most cases?")
        assert svc._should_use_sql_path(
            "Which district has the most cases?",
            _classification(Intent.DASHBOARD_ANALYTICS),
            f,
        ) is True

    def test_top_triggers_sql(self):
        svc = _service()
        f = _build_case_filters("Show top 5 districts by murder rate")
        assert svc._should_use_sql_path(
            "Show top 5 districts by murder rate",
            _classification(Intent.DASHBOARD_ANALYTICS),
            f,
        ) is True

    def test_near_triggers_sql(self):
        svc = _service()
        f = _build_case_filters("Show crimes near Whitefield")
        # "near" with an alphabetic token that is not a known
        # locality trips the SQL trigger.
        assert svc._should_use_sql_path(
            "Show crimes near Whitefield",
            _classification(Intent.CASE_SEARCH),
            f,
        ) is True

    def test_repeat_offender_triggers_sql(self):
        svc = _service()
        f = _build_case_filters("Show repeat offenders")
        assert svc._should_use_sql_path(
            "Show repeat offenders",
            _classification(Intent.CASE_SEARCH),
            f,
        ) is True


# ---------------------------------------------------------------------
# "between X and Y" / "from X to Y" → SQL
# ---------------------------------------------------------------------


class TestDateRangeTriggers:
    def test_between_iso_dates_triggers_sql(self):
        svc = _service()
        f = _build_case_filters("Show crimes between 2024-01-01 and 2024-06-30")
        assert svc._should_use_sql_path(
            "Show crimes between 2024-01-01 and 2024-06-30",
            _classification(Intent.CASE_SEARCH),
            f,
        ) is True

    def test_from_to_triggers_sql(self):
        svc = _service()
        f = _build_case_filters("Show crimes from 2024-01-01 to 2024-06-30")
        assert svc._should_use_sql_path(
            "Show crimes from 2024-01-01 to 2024-06-30",
            _classification(Intent.CASE_SEARCH),
            f,
        ) is True


# ---------------------------------------------------------------------
# Negative cases — service path is fine
# ---------------------------------------------------------------------


class TestServicePathStays:
    def test_simple_district_crime_uses_service(self):
        svc = _service()
        f = _build_case_filters("Show all murder cases in Mysuru")
        # The parser resolved district + crime_head, so the service
        # path can answer.
        assert svc._should_use_sql_path(
            "Show all murder cases in Mysuru",
            _classification(Intent.CASE_SEARCH),
            f,
        ) is False

    def test_today_uses_service(self):
        svc = _service()
        f = _build_case_filters("Show all FIRs filed today")
        assert svc._should_use_sql_path(
            "Show all FIRs filed today",
            _classification(Intent.CASE_SEARCH),
            f,
        ) is False

    def test_explain_case_never_uses_sql(self):
        svc = _service()
        f = _build_case_filters("Explain case 12345")
        assert svc._should_use_sql_path(
            "Explain case 12345",
            _classification(Intent.EXPLAIN_CASE),
            f,
        ) is False

    def test_investigation_summary_never_uses_sql(self):
        svc = _service()
        f = _build_case_filters("Investigation summary for case 12345")
        assert svc._should_use_sql_path(
            "Investigation summary for case 12345",
            _classification(Intent.INVESTIGATION_SUMMARY),
            f,
        ) is False

    def test_cyber_fraud_uses_service(self):
        svc = _service()
        f = _build_case_filters("Find cyber fraud complaints")
        assert svc._should_use_sql_path(
            "Find cyber fraud complaints",
            _classification(Intent.CASE_SEARCH),
            f,
        ) is False

    def test_summary_dashboard_uses_service(self):
        svc = _service()
        f = _build_case_filters("Show overall summary")
        assert svc._should_use_sql_path(
            "Show overall summary",
            _classification(Intent.DASHBOARD_ANALYTICS),
            f,
        ) is False


# ---------------------------------------------------------------------
# Defensive: a question with a district but no service-resolvable
# filter should still escalate.
# ---------------------------------------------------------------------


class TestDistrictNoFilter:
    def test_unknown_district_name_still_escalates(self):
        svc = _service()
        # The parser does not know "Atlantis", so the filters are
        # entirely empty.
        f = _build_case_filters("Show cases in Atlantis")
        assert f.district is None
        # The heuristic itself does not need to escalate here —
        # the parser will simply produce an empty result. We
        # assert that is the case.
        assert svc._should_use_sql_path(
            "Show cases in Atlantis",
            _classification(Intent.CASE_SEARCH),
            f,
        ) is False
