"""
Test fixtures.

The unit tests never touch a real database — they mock the SQLAlchemy
``Session`` so we can exercise the route + service layer in isolation.
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

# --- ensure the project root is on sys.path so ``backend.*`` imports work
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# --- AI settings: the validator refuses an empty GEMINI_API_KEY
# at startup, so we set a dummy value *before* importing settings.
# The actual key value is irrelevant — every test that touches
# the provider layer uses a client_factory that returns a mock.
os.environ.setdefault("GEMINI_API_KEY", "test-key")

from backend.config import settings  # noqa: E402
from backend.config.logging import configure_logging  # noqa: E402

# Configure logging once for the whole test session.
configure_logging()


# A bogus but valid-looking DSN so SQLAlchemy can construct the engine
# during the import chain without trying to connect.  get_db() is
# overridden in every test that needs it.
settings.database_url = (
    "postgresql+psycopg2://saaransh:saaransh@localhost:5432/saaransh_test"
)


# ---------------------------------------------------------------------
# Fake ORM objects — match the field names that the schemas read via
# ``from_attributes=True``.
# ---------------------------------------------------------------------


def make_district(district_id: int = 1, name: str = "Mysuru") -> SimpleNamespace:
    return SimpleNamespace(DistrictID=district_id, DistrictName=name)


def make_unit(
    unit_id: int = 1,
    name: str = "Mysuru City North PS",
    district: SimpleNamespace | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        UnitID=unit_id,
        UnitName=name,
        district=district if district is not None else make_district(),
    )


def make_status(status_id: int = 1, name: str = "Open") -> SimpleNamespace:
    return SimpleNamespace(CaseStatusID=status_id, CaseStatusName=name)


def make_crime_head(head_id: int = 1, name: str = "Crimes Against Property"):
    return SimpleNamespace(CrimeHeadID=head_id, CrimeGroupName=name)


def make_crime_sub_head(sub_id: int = 1, name: str = "Chain Snatching"):
    return SimpleNamespace(CrimeSubHeadID=sub_id, CrimeHeadName=name)


def make_category(cat_id: int = 1, name: str = "FIR") -> SimpleNamespace:
    return SimpleNamespace(CaseCategoryID=cat_id, LookupValue=name)


def make_gravity(gid: int = 1, name: str = "Heinous") -> SimpleNamespace:
    return SimpleNamespace(GravityOffenceID=gid, LookupValue=name)


def make_court(court_id: int = 1, name: str = "City Civil Court Mysuru"):
    return SimpleNamespace(CourtID=court_id, CourtName=name)


def make_employee(
    emp_id: int = 1, kgid: str = "KG-MYS-001", name: str = "Rajesh Kumar M"
) -> SimpleNamespace:
    return SimpleNamespace(EmployeeID=emp_id, KGID=kgid, FirstName=name)


def make_case(
    case_id: int = 1,
    crime_no: str = "104430001202400001",
    case_no: str = "202400001",
    registered: date | None = None,
    case_status: SimpleNamespace | None = None,
    case_category: SimpleNamespace | None = None,
    gravity: SimpleNamespace | None = None,
    major_head: SimpleNamespace | None = None,
    minor_head: SimpleNamespace | None = None,
    station: SimpleNamespace | None = None,
    **extras: Any,
) -> SimpleNamespace:
    """Build a CaseMaster-shaped SimpleNamespace for tests."""
    return SimpleNamespace(
        CaseMasterID=case_id,
        CrimeNo=crime_no,
        CaseNo=case_no,
        CrimeRegisteredDate=registered or date(2024, 1, 15),
        IncidentFromDate=datetime(2024, 1, 15, 9, 0, 0),
        IncidentToDate=None,
        InfoReceivedPSDate=None,
        latitude=12.3052,
        longitude=76.6551,
        BriefFacts="Test case brief facts.",
        mo_embedding=None,
        is_series_crime=False,
        series_id=None,
        created_at=datetime(2024, 1, 15, 9, 0, 0),
        # relationships
        police_station=station,
        investigating_officer=None,
        court=None,
        case_category=case_category or make_category(),
        gravity=gravity or make_gravity(),
        crime_major_head=major_head or make_crime_head(),
        crime_minor_head=minor_head or make_crime_sub_head(),
        case_status=case_status or make_status(),
        # children (overridden by get_case_detail tests)
        complainants=[],
        victims=[],
        accused=[],
        arrests=[],
        act_sections=[],
        chargesheet=None,
        evidence=[],
        recovered_items=[],
        # passthrough extras
        **extras,
    )


# ---------------------------------------------------------------------
# pytest fixtures
# ---------------------------------------------------------------------


@pytest.fixture
def case() -> SimpleNamespace:
    """A reasonable single-case object for most tests."""
    return make_case()


@pytest.fixture
def case_list(case) -> list[SimpleNamespace]:
    """Five cases, one of which is the base ``case``."""
    return [
        case,
        make_case(
            case_id=2,
            crime_no="104430001202400019",
            case_no="202400019",
            registered=date(2024, 3, 22),
        ),
        make_case(
            case_id=3,
            crime_no="104430001202400047",
            case_no="202400047",
            registered=date(2024, 6, 10),
        ),
        make_case(
            case_id=4,
            crime_no="104430002202400112",
            case_no="202400112",
            registered=date(2024, 2, 3),
        ),
        make_case(
            case_id=5,
            crime_no="104430002202400198",
            case_no="202400198",
            registered=date(2024, 4, 18),
        ),
    ]
