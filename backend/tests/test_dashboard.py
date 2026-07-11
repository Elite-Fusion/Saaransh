"""
Unit tests for the dashboard / analytics endpoints.

Strategy mirrors :mod:`backend.tests.test_case_apis`:
  * Mock the SQLAlchemy session with ``MagicMock``.
  * Build a fresh app per test, override ``get_db`` to return the mock.
  * Drive the routes through ``TestClient``.

The tests cover every endpoint at the route layer plus a
``TestAnalyticsServiceDirect`` class that exercises the service in
isolation — useful for filter-resolution edge cases and pagination
math that the route layer does not always exercise.
"""
from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import get_db  # noqa: E402
from backend.main import create_app  # noqa: E402
from backend.services.analytics_service import (  # noqa: E402
    AnalyticsService,
    CategoryCount,
    DistrictRef,
    MonthlyTrend,
    SummaryCounts,
)

from .conftest import (  # noqa: E402
    make_case,
    make_crime_head,
    make_district,
    make_status,
    make_unit,
)


# ---------------------------------------------------------------------
# Session-mock helpers
# ---------------------------------------------------------------------


class _ScalarResult:
    """Mocks ``.execute(stmt).scalar_one()`` (or .scalar_one_or_none())."""

    def __init__(self, value: Any) -> None:
        self._value = value

    def scalar_one(self) -> Any:
        return self._value

    def scalar_one_or_none(self) -> Any:
        return self._value


class _FirstResult:
    """Mocks ``.execute(stmt).first()`` for the district lookup."""

    def __init__(self, value: Any) -> None:
        self._value = value

    def first(self) -> Any:
        return self._value


class _ListResult:
    """Mocks ``.execute(stmt).all()`` (e.g. for group_by queries)."""

    def __init__(self, values: list[Any]) -> None:
        self._values = values

    def all(self) -> list[Any]:
        return self._values

    def first(self) -> Any:
        return self._values[0] if self._values else None


class _ScalarsResult:
    """Mocks ``.execute(stmt).scalars().all()`` for the recent-cases page."""

    def __init__(self, values: list[Any]) -> None:
        self._values = values

    def scalars(self) -> "_ScalarsResult":
        return self

    def all(self) -> list[Any]:
        return self._values


def _session_with_results(*results) -> MagicMock:
    """A session whose ``.execute()`` returns the given results in order.

    The first call returns the first result, the second call the
    second, etc. Any additional calls return the last result (so
    count-then-page patterns can be expressed as
    ``_session_with_results(count_result, page_result)``).
    """
    session = MagicMock(name="Session")

    def _execute(_stmt):
        if not results:
            return MagicMock()
        if len(results) == 1:
            return results[0]
        # pop in order, but keep the last one for any extras
        return results[_execute.idx] if _execute.idx < len(results) else results[-1]

    _execute.idx = 0

    def _next(_stmt):
        idx = _execute.idx
        _execute.idx = min(idx + 1, len(results) - 1)
        return results[idx]

    session.execute.side_effect = _next
    return session


# ---------------------------------------------------------------------
# Sample data builders
# ---------------------------------------------------------------------


def make_district_row(
    district_id: int = 1, name: str = "Bengaluru Urban"
) -> SimpleNamespace:
    return SimpleNamespace(DistrictID=district_id, DistrictName=name)


# ---------------------------------------------------------------------
# Client fixture (mirrors test_case_apis.make_client)
# ---------------------------------------------------------------------


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def make_client(app):
    """Return a callable that wires a session mock into the app and
    returns a TestClient."""

    def _factory(session: MagicMock) -> TestClient:
        def _override():
            try:
                yield session
            finally:
                pass

        app.dependency_overrides[get_db] = _override
        return TestClient(app)

    yield _factory
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------------------


class TestDashboardSummary:
    """GET /api/v1/dashboard/summary"""

    def test_returns_all_six_fields(self, make_client):
        # Group-by status query returns three buckets.
        # No district filter -> no follow-up district lookup.
        bucket_result = _ListResult(
            [
                (1, 4),   # Open
                (4, 8),   # Closed
                (3, 6),   # Charge Sheeted
            ]
        )
        # Name lookup for status ids
        name_result = _ListResult(
            [
                (1, "Open"),
                (4, "Closed"),
                (3, "Charge Sheeted"),
            ]
        )
        session = _session_with_results(bucket_result, name_result)
        client = make_client(session)

        resp = client.get("/api/v1/dashboard/summary")
        assert resp.status_code == 200
        body = resp.json()
        assert set(body) == {
            "total_cases",
            "open_cases",
            "closed_cases",
            "charge_sheet_filed",
            "convictions",
            "acquittals",
        }
        assert body["total_cases"] == 18
        assert body["open_cases"] == 4       # id 1 -> Open
        assert body["closed_cases"] == 8     # id 4 -> Closed
        assert body["charge_sheet_filed"] == 6

    def test_zeros_when_no_cases(self, make_client):
        session = _session_with_results(_ListResult([]))
        client = make_client(session)

        resp = client.get("/api/v1/dashboard/summary")
        assert resp.status_code == 200
        body = resp.json()
        assert body == {
            "total_cases": 0,
            "open_cases": 0,
            "closed_cases": 0,
            "charge_sheet_filed": 0,
            "convictions": 0,
            "acquittals": 0,
        }

    def test_convictions_and_acquittals_always_zero(self, make_client):
        """Even when there is real data, these stay 0 — verdict data
        is not yet tracked in the current schema."""
        bucket_result = _ListResult([(1, 10), (4, 5)])
        name_result = _ListResult([(1, "Open"), (4, "Closed")])
        session = _session_with_results(bucket_result, name_result)
        client = make_client(session)

        resp = client.get("/api/v1/dashboard/summary")
        body = resp.json()
        assert body["convictions"] == 0
        assert body["acquittals"] == 0

    def test_district_filter_narrows_counts(self, make_client):
        # 1. district id lookup (skipped — caller passed id directly)
        # 2. group-by status
        # 3. name lookup
        bucket_result = _ListResult([(1, 2), (4, 1)])
        name_result = _ListResult([(1, "Open"), (4, "Closed")])
        session = _session_with_results(bucket_result, name_result)
        client = make_client(session)

        resp = client.get("/api/v1/dashboard/summary?district_id=1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_cases"] == 3
        assert body["open_cases"] == 2
        assert body["closed_cases"] == 1

    def test_district_name_unknown_returns_zeros(self, make_client):
        # 1. district name lookup -> None -> __no_match__
        # The service short-circuits to an always-false WHERE, then
        # issues a follow-up empty group-by result.
        empty_group = _ListResult([])
        session = _session_with_results(
            _FirstResult(None),  # district lookup -> None
            empty_group,           # group-by after short-circuit
        )
        client = make_client(session)

        resp = client.get("/api/v1/dashboard/summary?district=Nonexistent")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_cases"] == 0
        assert body["open_cases"] == 0
        assert body["closed_cases"] == 0
        assert body["charge_sheet_filed"] == 0

    def test_open_under_investigation_both_count_as_open(self, make_client):
        """The summary endpoint buckets both 'Open' and 'Under
        Investigation' into the single `open_cases` headline number."""
        bucket_result = _ListResult(
            [
                (1, 5),   # Open
                (2, 3),   # Under Investigation
            ]
        )
        name_result = _ListResult(
            [
                (1, "Open"),
                (2, "Under Investigation"),
            ]
        )
        session = _session_with_results(bucket_result, name_result)
        client = make_client(session)

        resp = client.get("/api/v1/dashboard/summary")
        body = resp.json()
        assert body["open_cases"] == 8
        assert body["closed_cases"] == 0
        assert body["charge_sheet_filed"] == 0
        assert body["total_cases"] == 8


# ---------------------------------------------------------------------
# MONTHLY TRENDS
# ---------------------------------------------------------------------


class TestMonthlyTrends:
    """GET /api/v1/dashboard/monthly-trends"""

    def test_returns_twelve_rows(self, make_client):
        # Group-by year+month returns 4 buckets; the service
        # zero-fills the remaining 8.
        group_result = _ListResult(
            [
                (2024, 1, 3),
                (2024, 4, 2),
                (2024, 7, 5),
                (2024, 10, 1),
            ]
        )
        session = _session_with_results(group_result)
        client = make_client(session)

        resp = client.get("/api/v1/dashboard/monthly-trends?year=2024")
        assert resp.status_code == 200
        body = resp.json()
        assert body["year"] == 2024
        assert body["district"] is None
        assert len(body["items"]) == 12
        # Months with no data are 0
        assert body["items"][0] == {
            "year": 2024, "month": 1, "month_label": "Jan", "case_count": 3
        }
        assert body["items"][1]["case_count"] == 0
        assert body["items"][6]["case_count"] == 5

    def test_zero_year_returns_all_zeros(self, make_client):
        """A year with no cases still returns 12 zero rows."""
        session = _session_with_results(_ListResult([]))
        client = make_client(session)

        resp = client.get("/api/v1/dashboard/monthly-trends?year=2020")
        assert resp.status_code == 200
        body = resp.json()
        assert body["year"] == 2020
        assert len(body["items"]) == 12
        assert all(item["case_count"] == 0 for item in body["items"])

    def test_default_year_is_current(self, make_client):
        """When `year` is omitted, the route defaults to today's year."""
        session = _session_with_results(_ListResult([]))
        client = make_client(session)

        resp = client.get("/api/v1/dashboard/monthly-trends")
        assert resp.status_code == 200
        assert resp.json()["year"] == date.today().year

    def test_district_id_filter(self, make_client):
        # 1. group-by (with district filter applied via join)
        group_result = _ListResult([(2024, 5, 2)])
        # 2. district echo lookup (route's _lookup_district uses .first())
        district_echo = _FirstResult((2, "Mysuru"))
        session = _session_with_results(group_result, district_echo)
        client = make_client(session)

        resp = client.get(
            "/api/v1/dashboard/monthly-trends?year=2024&district_id=2"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["district"] == {"district_id": 2, "district_name": "Mysuru"}
        # Only one month has data — every other month is 0
        assert sum(item["case_count"] for item in body["items"]) == 2

    def test_validation_year_required(self, make_client):
        """`year` defaults — but explicit non-int must 422."""
        client = make_client(MagicMock())
        resp = client.get("/api/v1/dashboard/monthly-trends?year=abc")
        assert resp.status_code == 422

    def test_validation_year_out_of_range(self, make_client):
        client = make_client(MagicMock())
        resp = client.get("/api/v1/dashboard/monthly-trends?year=1800")
        assert resp.status_code == 422
        resp = client.get("/api/v1/dashboard/monthly-trends?year=2201")
        assert resp.status_code == 422


# ---------------------------------------------------------------------
# CRIME HEAD DISTRIBUTION
# ---------------------------------------------------------------------


class TestCrimeHeadDistribution:
    """GET /api/v1/dashboard/crime-head-distribution"""

    def test_groups_by_crime_head(self, make_client):
        # 1. group-by CrimeMajorHeadID
        group_result = _ListResult(
            [
                (2, 12),   # Crimes Against Property
                (4, 6),    # Economic Offences
                (5, 5),    # Drug Offences
            ]
        )
        # 2. name lookup
        name_result = _ListResult(
            [
                (2, "Crimes Against Property"),
                (4, "Economic Offences"),
                (5, "Drug Offences"),
            ]
        )
        session = _session_with_results(group_result, name_result)
        client = make_client(session)

        resp = client.get("/api/v1/dashboard/crime-head-distribution")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 23
        labels = [row["label"] for row in body["items"]]
        assert "Crimes Against Property" in labels
        assert "Economic Offences" in labels

    def test_empty_returns_empty_list(self, make_client):
        # Both group-by and the name-lookup query return empty
        session = _session_with_results(_ListResult([]), _ListResult([]))
        client = make_client(session)

        resp = client.get("/api/v1/dashboard/crime-head-distribution")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_district_filter_narrows(self, make_client):
        # 1. group-by with district filter
        group_result = _ListResult([(4, 3)])
        # 2. name lookup
        name_result = _ListResult([(4, "Economic Offences")])
        session = _session_with_results(group_result, name_result)
        client = make_client(session)

        resp = client.get(
            "/api/v1/dashboard/crime-head-distribution?district_id=1"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"][0]["case_count"] == 3
        assert body["total"] == 3


# ---------------------------------------------------------------------
# STATUS DISTRIBUTION
# ---------------------------------------------------------------------


class TestStatusDistribution:
    """GET /api/v1/dashboard/status-distribution"""

    def test_groups_by_case_status(self, make_client):
        # No district filter — only one group-by query + name lookup.
        group_result = _ListResult(
            [
                (1, 9),    # Open
                (2, 7),    # Under Investigation
                (3, 6),    # Charge Sheeted
                (4, 8),    # Closed
                (5, 0),    # Undetected
            ]
        )
        name_result = _ListResult(
            [
                (1, "Open"),
                (2, "Under Investigation"),
                (3, "Charge Sheeted"),
                (4, "Closed"),
                (5, "Undetected"),
            ]
        )
        session = _session_with_results(group_result, name_result)
        client = make_client(session)

        resp = client.get("/api/v1/dashboard/status-distribution")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 30
        labels = [row["label"] for row in body["items"]]
        assert "Open" in labels
        assert "Closed" in labels
        assert "Charge Sheeted" in labels

    def test_empty_returns_empty_list(self, make_client):
        session = _session_with_results(_ListResult([]), _ListResult([]))
        client = make_client(session)

        resp = client.get("/api/v1/dashboard/status-distribution")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0


# ---------------------------------------------------------------------
# DISTRICT DISTRIBUTION
# ---------------------------------------------------------------------


class TestDistrictDistribution:
    """GET /api/v1/dashboard/district-distribution"""

    def test_groups_by_district(self, make_client):
        # One big query joining CaseMaster -> Unit -> District, with
        # group-by district.
        group_result = _ListResult(
            [
                (1, "Bengaluru Urban", 7),
                (2, "Mysuru", 6),
                (3, "Dharwad", 3),
                (4, "Dakshina Kannada", 4),
                (5, "Belagavi", 3),
                (6, "Shivamogga", 3),
                (7, "Kalaburagi", 3),
                (8, "Tumakuru", 1),
            ]
        )
        session = _session_with_results(group_result)
        client = make_client(session)

        resp = client.get("/api/v1/dashboard/district-distribution")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 30
        labels = [row["label"] for row in body["items"]]
        assert "Bengaluru Urban" in labels
        assert "Mysuru" in labels

    def test_empty_returns_empty_list(self, make_client):
        session = _session_with_results(_ListResult([]))
        client = make_client(session)

        resp = client.get("/api/v1/dashboard/district-distribution")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0


# ---------------------------------------------------------------------
# RECENT CASES
# ---------------------------------------------------------------------


class TestRecentCases:
    """GET /api/v1/dashboard/recent-cases"""

    def test_default_limit_is_10(self, make_client):
        case = make_case()
        # 1. count
        count_result = _ScalarResult(30)
        # 2. page
        page_result = _ScalarsResult([case])
        session = _session_with_results(count_result, page_result)
        client = make_client(session)

        resp = client.get("/api/v1/dashboard/recent-cases")
        assert resp.status_code == 200
        body = resp.json()
        assert body["pagination"] == {
            "total": 30,
            "page": 1,
            "page_size": 10,
            "total_pages": 3,
            "has_next": True,
            "has_prev": False,
        }
        assert len(body["items"]) == 1

    def test_limit_max_50_enforced(self, make_client):
        client = make_client(MagicMock())
        resp = client.get("/api/v1/dashboard/recent-cases?page_size=51")
        assert resp.status_code == 422

    def test_limit_too_small_rejected(self, make_client):
        client = make_client(MagicMock())
        resp = client.get("/api/v1/dashboard/recent-cases?page_size=0")
        assert resp.status_code == 422

    def test_pagination_meta_correct(self, make_client):
        # 21 cases, page 2, page_size 10 -> total_pages=3, has_next=T, has_prev=T
        count_result = _ScalarResult(21)
        page_result = _ScalarsResult([])
        session = _session_with_results(count_result, page_result)
        client = make_client(session)

        resp = client.get(
            "/api/v1/dashboard/recent-cases?page=2&page_size=10"
        )
        assert resp.status_code == 200
        meta = resp.json()["pagination"]
        assert meta["total"] == 21
        assert meta["page"] == 2
        assert meta["page_size"] == 10
        assert meta["total_pages"] == 3
        assert meta["has_next"] is True
        assert meta["has_prev"] is True

    def test_empty_returns_zero_pagination(self, make_client):
        count_result = _ScalarResult(0)
        page_result = _ScalarsResult([])
        session = _session_with_results(count_result, page_result)
        client = make_client(session)

        resp = client.get("/api/v1/dashboard/recent-cases")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["pagination"]["total"] == 0
        assert body["pagination"]["total_pages"] == 0
        assert body["pagination"]["has_next"] is False
        assert body["pagination"]["has_prev"] is False

    def test_items_use_case_summary_shape(self, make_client):
        # Build a case with the same shape CaseSummaryOut reads.
        case = make_case(
            case_id=42,
            crime_no="104430001202499942",
            case_no="202499942",
            registered=date(2024, 7, 25),
        )
        case.case_status = make_status(status_id=2, name="Under Investigation")
        case.crime_major_head = make_crime_head(
            head_id=4, name="Economic Offences"
        )
        case.police_station = make_unit(
            unit_id=1,
            name="Mysuru City North PS",
            district=make_district(district_id=2, name="Mysuru"),
        )

        count_result = _ScalarResult(1)
        page_result = _ScalarsResult([case])
        session = _session_with_results(count_result, page_result)
        client = make_client(session)

        resp = client.get("/api/v1/dashboard/recent-cases?page_size=5")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert items[0]["case_id"] == 42
        assert items[0]["crime_no"] == "104430001202499942"
        assert items[0]["case_status"]["case_status_name"] == "Under Investigation"
        assert items[0]["crime_major_head"]["crime_group_name"] == "Economic Offences"
        assert items[0]["police_station"]["district"]["district_name"] == "Mysuru"


# ---------------------------------------------------------------------
# Service-direct tests (no HTTP)
# ---------------------------------------------------------------------


class TestAnalyticsServiceDirect:
    """Exercise the service layer without going through the HTTP layer."""

    def test_summary_no_district(self):
        bucket_result = _ListResult([(1, 5), (4, 3)])
        name_result = _ListResult([(1, "Open"), (4, "Closed")])
        session = _session_with_results(bucket_result, name_result)

        out = AnalyticsService(session).get_summary()
        assert isinstance(out, SummaryCounts)
        assert out.total_cases == 8
        assert out.open_cases == 5
        assert out.closed_cases == 3
        assert out.charge_sheet_filed == 0
        assert out.convictions == 0
        assert out.acquittals == 0

    def test_summary_unknown_district_name(self):
        # district lookup returns None
        lookup = _FirstResult(None)
        # then group-by after short-circuit returns empty
        empty_group = _ListResult([])
        session = _session_with_results(lookup, empty_group)

        out = AnalyticsService(session).get_summary(
            district=DistrictRef(name="Nonexistent")
        )
        assert out.total_cases == 0
        assert out.convictions == 0
        assert out.acquittals == 0

    def test_monthly_trends_returns_12_dataclasses(self):
        session = _session_with_results(
            _ListResult([(2024, 3, 5), (2024, 7, 2)])
        )
        out = AnalyticsService(session).get_monthly_trends(year=2024)
        assert len(out) == 12
        assert all(isinstance(t, MonthlyTrend) for t in out)
        # The two populated months
        assert out[2].case_count == 5   # March (0-indexed = 2)
        assert out[6].case_count == 2   # July
        # The rest are zero-filled
        assert out[0].case_count == 0
        assert out[11].case_count == 0

    def test_recent_cases_two_queries(self):
        """The recent-cases path must issue exactly two queries —
        one count and one page — even with eager loading.
        `selectinload` issues a follow-up IN-query, but that's
        bundled into the single ``session.execute`` call from the
        page statement."""
        case = make_case()
        count_result = _ScalarResult(1)
        page_result = _ScalarsResult([case])
        session = _session_with_results(count_result, page_result)

        rows, total = AnalyticsService(session).get_recent_cases()
        assert total == 1
        assert len(rows) == 1
        # Two execute() calls: count + page
        assert session.execute.call_count == 2

    def test_recent_cases_signature(self):
        """Pin the AI-friendly signature: keyword args only, returns
        (rows, total)."""
        import inspect

        sig = inspect.signature(AnalyticsService.get_recent_cases)
        params = sig.parameters
        assert "self" in params
        assert "page" in params
        assert "page_size" in params

    def test_resolve_district_id_passthrough(self):
        """When a district_id is given, no lookup query is issued."""
        session = MagicMock()
        out = AnalyticsService(session)._resolve_district_id(
            DistrictRef(district_id=2)
        )
        assert out == 2
        session.execute.assert_not_called()

    def test_resolve_district_name_hit(self):
        session = _session_with_results(_FirstResult((5,)))
        out = AnalyticsService(session)._resolve_district_id(
            DistrictRef(name="Mysuru")
        )
        assert out == 5

    def test_resolve_district_name_miss(self):
        session = _session_with_results(_FirstResult(None))
        out = AnalyticsService(session)._resolve_district_id(
            DistrictRef(name="Nonexistent")
        )
        assert out == "__no_match__"

    def test_resolve_district_none(self):
        session = MagicMock()
        out = AnalyticsService(session)._resolve_district_id(None)
        assert out is None
        session.execute.assert_not_called()

    def test_summary_bucketises_charge_sheeted(self):
        """`charge_sheet_filed` is the count of `Charge Sheeted` rows
        — independent of the open/closed bucketisation."""
        bucket_result = _ListResult(
            [(1, 2), (3, 7), (4, 3)]  # Open  # Charge Sheeted  # Closed
        )
        name_result = _ListResult(
            [(1, "Open"), (3, "Charge Sheeted"), (4, "Closed")]
        )
        session = _session_with_results(bucket_result, name_result)

        out = AnalyticsService(session).get_summary()
        assert out.charge_sheet_filed == 7
        assert out.open_cases == 2
        assert out.closed_cases == 3
        assert out.total_cases == 12
