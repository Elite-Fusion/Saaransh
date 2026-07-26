"""
Tests for the natural-language → :class:`CaseFilters` parser
(``_build_case_filters`` in :mod:`backend.ai.services.investigation_service`).

The parser is the heart of the service-method fast path: if it
correctly maps a question to a :class:`CaseFilters` value, the
orchestrator can serve the question without invoking the LLM at
all. The tests in this file pin the parser's behaviour to the
keywords the public verification list uses.
"""
from __future__ import annotations

from datetime import date

from backend.ai.services.investigation_service import _build_case_filters


# ---------------------------------------------------------------------
# District parsing
# ---------------------------------------------------------------------


class TestParseDistrict:
    def test_mysuru(self):
        f = _build_case_filters("Show all murder cases in Mysuru")
        assert f.district == "Mysuru"
        assert f.crime_head == "Murder"

    def test_mysore_legacy(self):
        f = _build_case_filters("cases in Mysore district")
        assert f.district == "Mysuru"

    def test_bengaluru(self):
        f = _build_case_filters("theft cases in Bengaluru")
        assert f.district == "Bengaluru"
        assert f.crime_head == "Theft"

    def test_bangalore_legacy(self):
        f = _build_case_filters("cases in Bangalore")
        assert f.district == "Bengaluru"

    def test_hassan(self):
        f = _build_case_filters("robbery cases in Hassan")
        assert f.district == "Hassan"
        assert f.crime_head == "Robbery"

    def test_no_district_means_none(self):
        f = _build_case_filters("Show all murder cases")
        assert f.district is None
        assert f.crime_head == "Murder"


# ---------------------------------------------------------------------
# Crime-head parsing
# ---------------------------------------------------------------------


class TestParseCrimeHead:
    def test_murder(self):
        f = _build_case_filters("Show all murder cases")
        assert f.crime_head == "Murder"

    def test_theft(self):
        f = _build_case_filters("List theft FIRs")
        assert f.crime_head == "Theft"

    def test_cyber_fraud(self):
        f = _build_case_filters("Find cyber fraud complaints")
        assert f.crime_head == "Cyber Fraud"

    def test_cyber_crime_alternate(self):
        f = _build_case_filters("Find cyber crime complaints")
        assert f.crime_head == "Cyber Crime"

    def test_chain_snatching(self):
        f = _build_case_filters("Find chain snatching cases")
        assert f.crime_head == "Chain Snatching"

    def test_no_crime(self):
        f = _build_case_filters("Show all cases")
        assert f.crime_head is None


# ---------------------------------------------------------------------
# Status parsing
# ---------------------------------------------------------------------


class TestParseStatus:
    def test_open(self):
        f = _build_case_filters("Show open cases")
        assert f.status == "Open"

    def test_pending(self):
        f = _build_case_filters("Show pending investigations")
        assert f.status == "Under Investigation"

    def test_under_investigation(self):
        f = _build_case_filters("Show cases under investigation")
        assert f.status == "Under Investigation"

    def test_charge_sheeted(self):
        f = _build_case_filters("Show charge sheeted cases")
        assert f.status == "Charge Sheeted"

    def test_chargesheeted_compact(self):
        f = _build_case_filters("Show chargesheeted cases")
        assert f.status == "Charge Sheeted"

    def test_closed(self):
        f = _build_case_filters("Show closed cases")
        assert f.status == "Closed"


# ---------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------


class TestParseDates:
    def test_today(self):
        f = _build_case_filters("Show all FIRs filed today")
        today = date.today()
        assert f.date_from == today
        assert f.date_to == today

    def test_yesterday(self):
        from datetime import timedelta

        f = _build_case_filters("cases filed yesterday")
        yesterday = date.today() - timedelta(days=1)
        assert f.date_from == yesterday
        assert f.date_to == yesterday

    def test_last_7_days(self):
        from datetime import timedelta

        f = _build_case_filters("Show cases from last 7 days")
        today = date.today()
        assert f.date_to == today
        assert f.date_from == today - timedelta(days=7)

    def test_last_30_days(self):
        from datetime import timedelta

        f = _build_case_filters("cases in last 30 days")
        today = date.today()
        assert f.date_to == today
        assert f.date_from == today - timedelta(days=30)

    def test_this_week(self):
        from datetime import timedelta

        f = _build_case_filters("cases this week")
        today = date.today()
        # Monday of this week
        expected_start = today - timedelta(days=today.weekday())
        assert f.date_from == expected_start
        assert f.date_to == today

    def test_this_month(self):
        f = _build_case_filters("cases this month")
        today = date.today()
        assert f.date_from == today.replace(day=1)
        assert f.date_to == today

    def test_between_iso_dates(self):
        f = _build_case_filters(
            "Show crimes between 2024-01-01 and 2024-06-30"
        )
        assert f.date_from == date(2024, 1, 1)
        assert f.date_to == date(2024, 6, 30)

    def test_in_year(self):
        f = _build_case_filters("cases in 2024")
        assert f.date_from == date(2024, 1, 1)
        assert f.date_to == date(2024, 12, 31)

    def test_no_dates(self):
        f = _build_case_filters("show cases")
        assert f.date_from is None
        assert f.date_to is None


# ---------------------------------------------------------------------
# Locality → district
# ---------------------------------------------------------------------


class TestParseLocality:
    def test_whitefield(self):
        f = _build_case_filters("Show crimes near Whitefield")
        assert f.district == "Bengaluru"
        assert f.police_station == "Whitefield"

    def test_indiranagar(self):
        f = _build_case_filters("robbery near Indiranagar")
        assert f.district == "Bengaluru"
        assert f.crime_head == "Robbery"

    def test_unknown_locality_no_district(self):
        f = _build_case_filters("Show crimes near Atlantis")
        # Unknown locality does not set a district; the orchestrator
        # will fall through to the SQL path.
        assert f.district is None


# ---------------------------------------------------------------------
# FIR number
# ---------------------------------------------------------------------


class TestParseFIR:
    def test_fir_number(self):
        f = _build_case_filters("Show FIR 104430003202400098")
        assert f.fir_number == "104430003202400098"

    def test_fir_takes_precedence(self):
        # When an FIR is present the parser does not pick up other
        # filters — the case service short-circuits on fir_number.
        f = _build_case_filters("Show FIR 104430003202400098 in Mysuru")
        assert f.fir_number == "104430003202400098"
        assert f.district is None


# ---------------------------------------------------------------------
# Combined parsing
# ---------------------------------------------------------------------


class TestParseCombined:
    def test_district_plus_crime_plus_date(self):
        f = _build_case_filters(
            "Show all murder cases in Mysuru in last 30 days"
        )
        assert f.district == "Mysuru"
        assert f.crime_head == "Murder"
        assert f.date_to == date.today()
        assert f.date_from is not None

    def test_status_plus_crime(self):
        f = _build_case_filters("Show open murder cases")
        assert f.crime_head == "Murder"
        assert f.status == "Open"

    def test_unknown_question_returns_empty_filters(self):
        f = _build_case_filters("What is the meaning of life?")
        # All the named fields stay None.
        for name in (
            "fir_number",
            "district",
            "crime_head",
            "status",
            "date_from",
            "date_to",
        ):
            assert getattr(f, name) is None

    def test_empty_question_returns_empty_filters(self):
        f = _build_case_filters("")
        for name in (
            "district",
            "crime_head",
            "status",
            "date_from",
            "date_to",
        ):
            assert getattr(f, name) is None
