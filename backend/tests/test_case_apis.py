"""
Unit tests for the case APIs.

The tests mock the SQLAlchemy ``Session`` so we can drive the route +
service layer end-to-end without a live database.  The strategy:

  * Build a fresh app per test.
  * Override the ``get_db`` dependency on the app to return a single
    mock session.
  * Use :class:`fastapi.testclient.TestClient` to exercise the routes.

Every test is a hermetic unit test — no fixtures persist between tests.
"""
from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.database import get_db
from backend.main import create_app
from backend.services.case_service import (
    ALLOWED_SORT_FIELDS,
    CaseFilters,
    CaseNotFoundError,
    CaseService,
    CaseSort,
)

from .conftest import (
    make_case,
    make_court,
    make_crime_head,
    make_crime_sub_head,
    make_employee,
    make_status,
    make_unit,
)

# ---------------------------------------------------------------------
# Session-mock helpers
# ---------------------------------------------------------------------


class _ScalarOneResult:
    """Mocks the ``.execute(stmt).scalar_one_or_none()`` chain."""

    def __init__(self, value: Any) -> None:
        self._value = value

    def scalar_one_or_none(self) -> Any:
        return self._value


class _ScalarResult:
    """Mocks the ``.execute(stmt).scalars().all()`` chain."""

    def __init__(self, values: list[Any]) -> None:
        self._values = values

    def scalars(self) -> "_ScalarResult":
        return self

    def all(self) -> list[Any]:
        return self._values


def _session_list_with(rows: list[Any], total: int) -> MagicMock:
    """A session that returns ``total`` for the count query and ``rows``
    for the page query."""
    session = MagicMock(name="Session")

    count_result = MagicMock()
    count_result.scalar_one.return_value = total
    page_result = _ScalarResult(rows)

    session.execute.side_effect = [count_result, page_result]
    return session


def _session_detail(case: Any | None) -> MagicMock:
    """A session whose execute() returns ``scalar_one_or_none() = case``."""
    session = MagicMock(name="Session")
    result = MagicMock()
    result.scalar_one_or_none.return_value = case
    session.execute.return_value = result
    return session


# ---------------------------------------------------------------------
# Client fixture
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
# LIST endpoint
# ---------------------------------------------------------------------


class TestListCases:
    def test_returns_paginated_envelope(self, make_client):
        case = make_case()
        client = make_client(_session_list_with([case], total=1))

        resp = client.get("/api/v1/cases?page=1&page_size=20")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "pagination" in body
        meta = body["pagination"]
        assert meta == {
            "total": 1,
            "page": 1,
            "page_size": 20,
            "total_pages": 1,
            "has_next": False,
            "has_prev": False,
        }
        assert len(body["items"]) == 1
        assert body["items"][0]["case_id"] == 1
        assert body["items"][0]["crime_no"] == "104430001202400001"

    def test_pagination_math(self, make_client):
        # 21 items, page=2, page_size=10 -> total_pages=3, has_prev=True, has_next=True
        client = make_client(_session_list_with([], total=21))
        resp = client.get("/api/v1/cases?page=2&page_size=10")
        assert resp.status_code == 200
        meta = resp.json()["pagination"]
        assert meta["total"] == 21
        assert meta["page"] == 2
        assert meta["page_size"] == 10
        assert meta["total_pages"] == 3
        assert meta["has_next"] is True
        assert meta["has_prev"] is True

    def test_pagination_empty(self, make_client):
        client = make_client(_session_list_with([], total=0))
        resp = client.get("/api/v1/cases")
        assert resp.status_code == 200
        meta = resp.json()["pagination"]
        assert meta["total"] == 0
        assert meta["total_pages"] == 0
        assert meta["has_next"] is False
        assert meta["has_prev"] is False

    def test_filter_fir_number(self, make_client):
        case = make_case()
        client = make_client(_session_list_with([case], total=1))
        resp = client.get("/api/v1/cases?fir_number=104430001202400001")
        assert resp.status_code == 200
        assert resp.json()["items"][0]["crime_no"] == "104430001202400001"

    def test_filter_district_by_id(self, make_client):
        case = make_case()
        client = make_client(_session_list_with([case], total=1))
        resp = client.get("/api/v1/cases?district_id=2")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1

    def test_filter_district_by_name(self, make_client):
        """When the caller passes a name, the service queries the lookup
        first to resolve it to an id.  The first ``execute()`` returns
        the lookup row; the second returns the count; the third returns
        the page.
        """
        case = make_case()
        session = MagicMock(name="Session")

        # 1. district lookup -> id
        district_lookup = MagicMock()
        district_lookup.first.return_value = (2,)
        # 2. count
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        # 3. page
        page_result = _ScalarResult([case])

        session.execute.side_effect = [district_lookup, count_result, page_result]
        client = make_client(session)

        resp = client.get("/api/v1/cases?district=Mysuru")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1

    def test_filter_police_station_by_id(self, make_client):
        case = make_case()
        client = make_client(_session_list_with([case], total=1))
        resp = client.get("/api/v1/cases?police_station_id=1")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1

    def test_filter_crime_head_by_id(self, make_client):
        case = make_case()
        client = make_client(_session_list_with([case], total=1))
        resp = client.get("/api/v1/cases?crime_head_id=2")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1

    def test_filter_crime_sub_head_by_id(self, make_client):
        case = make_case()
        client = make_client(_session_list_with([case], total=1))
        resp = client.get("/api/v1/cases?crime_sub_head_id=6")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1

    def test_filter_status_by_id(self, make_client):
        case = make_case()
        client = make_client(_session_list_with([case], total=1))
        resp = client.get("/api/v1/cases?status_id=4")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1

    def test_filter_date_range(self, make_client):
        case = make_case()
        client = make_client(_session_list_with([case], total=1))
        resp = client.get(
            "/api/v1/cases?date_from=2024-01-01&date_to=2024-12-31"
        )
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1

    def test_unknown_district_name_returns_empty(self, make_client):
        """Unknown name -> no match sentinel -> 0 rows, 200."""
        # Call 1: district lookup -> None
        # Call 2: count -> 0 (because of where(False))
        # Call 3: page (never produces results because count was 0 but is still executed)
        lookup = MagicMock()
        lookup.first.return_value = None
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        page_result = _ScalarResult([])
        session = MagicMock()
        session.execute.side_effect = [lookup, count_result, page_result]
        client = make_client(session)

        resp = client.get("/api/v1/cases?district=Nonexistent")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["pagination"]["total"] == 0

    # ---- sort whitelist -------------------------------------------

    def test_sort_whitelist_default(self, make_client):
        client = make_client(_session_list_with([], total=0))
        resp = client.get("/api/v1/cases")
        assert resp.status_code == 200

    @pytest.mark.parametrize("field", sorted(ALLOWED_SORT_FIELDS))
    def test_sort_whitelist_each_field(self, make_client, field):
        client = make_client(_session_list_with([], total=0))
        resp = client.get(f"/api/v1/cases?sort_by={field}")
        assert resp.status_code == 200, resp.text

    def test_sort_invalid_field_rejected(self, make_client):
        client = make_client(MagicMock())
        resp = client.get("/api/v1/cases?sort_by=drop_table")
        assert resp.status_code == 400
        body = resp.json()
        assert body["detail"]["code"] == "INVALID_SORT_FIELD"

    def test_sort_invalid_order_rejected(self, make_client):
        client = make_client(MagicMock())
        resp = client.get("/api/v1/cases?sort_order=sideways")
        assert resp.status_code == 400
        body = resp.json()
        assert body["detail"]["code"] == "INVALID_SORT_ORDER"

    # ---- validation -------------------------------------------------

    def test_validation_page_size_too_large(self, make_client):
        client = make_client(MagicMock())
        resp = client.get("/api/v1/cases?page_size=500")
        assert resp.status_code == 422

    def test_validation_negative_page(self, make_client):
        client = make_client(MagicMock())
        resp = client.get("/api/v1/cases?page=0")
        assert resp.status_code == 422

    def test_validation_invalid_date(self, make_client):
        client = make_client(MagicMock())
        resp = client.get("/api/v1/cases?date_from=not-a-date")
        assert resp.status_code == 422


# ---------------------------------------------------------------------
# DETAIL endpoint
# ---------------------------------------------------------------------


class TestGetCase:
    def test_returns_complete_case(self, make_client):
        # Build a case with all sub-collections populated.
        case = make_case()
        case.court = make_court()
        case.investigating_officer = make_employee()
        case.complainants = [
            SimpleNamespace(
                ComplainantID=1,
                CaseMasterID=1,
                ComplainantName="Lakshmi Devi R",
                AgeYear=52,
                GenderID=2,
                OccupationID=1,
                ReligionID=1,
                CasteID=4,
            )
        ]
        case.victims = [
            SimpleNamespace(
                VictimMasterID=1,
                CaseMasterID=1,
                VictimName="Lakshmi Devi R",
                AgeYear=52,
                GenderID=2,
                VictimPolice="0",
                photo_url=None,
                photo_hash=None,
            )
        ]
        case.accused = [
            SimpleNamespace(
                AccusedMasterID=1,
                CaseMasterID=1,
                AccusedName="Sunil Kumar B",
                AgeYear=28,
                GenderID=1,
                PersonID="A1",
                address=None,
                is_known_criminal=True,
                criminal_history="Chain snatching 2020, 2022",
                photo_url=None,
                photo_hash=None,
            )
        ]
        case.evidence = []
        case.recovered_items = [
            SimpleNamespace(
                RecoveryID=1,
                CaseMasterID=1,
                AccusedMasterID=1,
                item_description="Gold chain recovered",
                quantity="1",
                estimated_value=45000.00,
                photo_url=None,
                photo_hash=None,
                recovery_date=datetime(2024, 1, 21),
                recovery_location="Bannimantap",
                recovered_by=1,
                witness_name="Ramu",
                seizure_memo_ref="SM/2024/001",
            )
        ]
        case.act_sections = [
            SimpleNamespace(
                CaseMasterID=1,
                ActID="IPC",
                SectionID="379",
                ActOrderID=1,
                SectionOrderID=1,
                act=SimpleNamespace(
                    ActCode="IPC",
                    ShortName="IPC",
                    ActDescription="Indian Penal Code",
                ),
            )
        ]
        case.chargesheet = None

        client = make_client(_session_detail(case))
        resp = client.get("/api/v1/cases/1")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["case_id"] == 1
        assert body["crime_no"] == "104430001202400001"
        assert len(body["complainants"]) == 1
        assert body["complainants"][0]["complainant_name"] == "Lakshmi Devi R"
        assert len(body["victims"]) == 1
        assert body["victims"][0]["victim_name"] == "Lakshmi Devi R"
        assert len(body["accused"]) == 1
        assert body["accused"][0]["accused_name"] == "Sunil Kumar B"
        assert len(body["recovered_items"]) == 1
        assert body["recovered_items"][0]["item_description"].startswith("Gold")
        assert len(body["act_sections"]) == 1
        assert body["act_sections"][0]["act_code"] == "IPC"
        assert body["act_sections"][0]["section_code"] == "379"
        assert body["chargesheet"] is None
        assert body["case_status"]["case_status_name"] == "Open"

    def test_404_when_not_found(self, make_client):
        client = make_client(_session_detail(None))
        resp = client.get("/api/v1/cases/99999")
        assert resp.status_code == 404
        body = resp.json()
        assert body["detail"]["code"] == "CASE_NOT_FOUND"
        assert body["detail"]["details"]["case_id"] == 99999

    def test_validation_invalid_id(self, make_client):
        client = make_client(MagicMock())
        resp = client.get("/api/v1/cases/0")
        assert resp.status_code == 422


# ---------------------------------------------------------------------
# Service-level direct tests (no FastAPI)
# ---------------------------------------------------------------------


class TestCaseServiceDirect:
    """Cover the service layer without going through HTTP."""

    def test_list_cases_returns_rows_and_total(self):
        case = make_case()
        session = _session_list_with([case], total=1)
        svc = CaseService(session)
        rows, total = svc.list_cases(
            filters=CaseFilters(),
            page=1,
            page_size=20,
            sort=CaseSort(field="crime_registered_date", order="desc"),
        )
        assert total == 1
        assert len(rows) == 1

    def test_list_cases_invalid_sort_raises(self):
        session = MagicMock()
        svc = CaseService(session)
        with pytest.raises(ValueError):
            svc.list_cases(
                filters=CaseFilters(),
                page=1,
                page_size=20,
                sort=CaseSort(field="__nope__", order="asc"),
            )

    def test_get_case_detail_not_found(self):
        session = _session_detail(None)
        svc = CaseService(session)
        with pytest.raises(CaseNotFoundError) as excinfo:
            svc.get_case_detail(42)
        assert excinfo.value.case_id == 42

    def test_get_case_detail_returns_case(self):
        case = make_case()
        session = _session_detail(case)
        svc = CaseService(session)
        out = svc.get_case_detail(1)
        assert out is case


# ---------------------------------------------------------------------
# Pagination utility
# ---------------------------------------------------------------------


class TestPaginationUtil:
    def test_first_page(self):
        from backend.utils.pagination import calculate_pagination

        meta = calculate_pagination(page=1, page_size=20, total=100)
        assert meta.has_next is True
        assert meta.has_prev is False
        assert meta.total_pages == 5

    def test_middle_page(self):
        from backend.utils.pagination import calculate_pagination

        meta = calculate_pagination(page=3, page_size=20, total=100)
        assert meta.has_next is True
        assert meta.has_prev is True

    def test_last_page(self):
        from backend.utils.pagination import calculate_pagination

        meta = calculate_pagination(page=5, page_size=20, total=100)
        assert meta.has_next is False
        assert meta.has_prev is True

    def test_partial_last_page(self):
        from backend.utils.pagination import calculate_pagination

        meta = calculate_pagination(page=3, page_size=20, total=55)
        assert meta.total_pages == 3
        assert meta.has_next is False

    def test_empty(self):
        from backend.utils.pagination import calculate_pagination

        meta = calculate_pagination(page=1, page_size=20, total=0)
        assert meta.total_pages == 0
        assert meta.has_next is False
        assert meta.has_prev is False
