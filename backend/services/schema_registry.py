"""
Schema registry — the **single source of truth** for the SQL
allowlist used by the AI investigation engine.

The Phase 6 :class:`~backend.ai.services.sql_validation_service.SQLValidationService`
rejects any SQL that references a table not in :data:`SCHEMA_TABLES` or a
column not in that table's column set. The constants below mirror
:file:`database/schema/ksp_real_schema.sql` exactly — a drift test in
:mod:`backend.tests.test_services.test_schema_registry` parses the SQL
schema and asserts every ``CREATE TABLE`` and its columns is reflected
here.

Why this lives in :mod:`backend.services` and not :mod:`backend.ai`?

The Phase 5 independence test
(:mod:`backend.tests.test_ai.test_ai_independence`) forbids any
``backend/ai/**`` file from importing ``backend.database``,
``backend.models``, or ``sqlalchemy``. The AI services use this
registry through a Protocol / a thin :class:`AIQueryService` facade so
the AI layer stays free of database imports. The registry itself is
plain data — ``frozenset`` of strings — and has no runtime dependency
on SQLAlchemy. We keep it under ``services`` for consistency with the
existing layout and to make the drift test a one-liner.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Mapping


# ---------------------------------------------------------------------
# Per-table column allowlists
# ---------------------------------------------------------------------
# These mirror ``database/schema/ksp_real_schema.sql``. Keep them in
# alphabetical order within each constant to make drift easy to spot.

STATE_COLS: frozenset[str] = frozenset(
    {"StateID", "StateName", "NationalityID", "Active"}
)
DISTRICT_COLS: frozenset[str] = frozenset(
    {"DistrictID", "DistrictName", "StateID", "Active"}
)
UNIT_TYPE_COLS: frozenset[str] = frozenset(
    {"UnitTypeID", "UnitTypeName", "CityDistState", "Hierarchy", "Active"}
)
UNIT_COLS: frozenset[str] = frozenset(
    {
        "UnitID",
        "UnitName",
        "TypeID",
        "ParentUnit",
        "StateID",
        "DistrictID",
        "latitude",
        "longitude",
        "Active",
    }
)
RANK_COLS: frozenset[str] = frozenset(
    {"RankID", "RankName", "Hierarchy", "Active"}
)
DESIGNATION_COLS: frozenset[str] = frozenset(
    {"DesignationID", "DesignationName", "SortOrder", "Active"}
)
EMPLOYEE_COLS: frozenset[str] = frozenset(
    {
        "EmployeeID",
        "DistrictID",
        "UnitID",
        "RankID",
        "DesignationID",
        "KGID",
        "FirstName",
        "EmployeeDOB",
        "GenderID",
        "BloodGroupID",
        "PhysicallyChallenged",
        "AppointmentDate",
        "Active",
    }
)
COURT_COLS: frozenset[str] = frozenset(
    {"CourtID", "CourtName", "DistrictID", "StateID", "Active"}
)
CASE_CATEGORY_COLS: frozenset[str] = frozenset(
    {"CaseCategoryID", "LookupValue"}
)
GRAVITY_COLS: frozenset[str] = frozenset(
    {"GravityOffenceID", "LookupValue"}
)
CASE_STATUS_COLS: frozenset[str] = frozenset(
    {"CaseStatusID", "CaseStatusName"}
)
CRIME_HEAD_COLS: frozenset[str] = frozenset(
    {"CrimeHeadID", "CrimeGroupName", "Active"}
)
CRIME_SUB_HEAD_COLS: frozenset[str] = frozenset(
    {"CrimeSubHeadID", "CrimeHeadID", "CrimeHeadName", "SeqID", "Active"}
)
ACT_COLS: frozenset[str] = frozenset(
    {"ActCode", "ActDescription", "ShortName", "Active"}
)
SECTION_COLS: frozenset[str] = frozenset(
    {"SectionCode", "ActCode", "SectionDescription", "Active"}
)
CRIME_HEAD_ACT_SECTION_COLS: frozenset[str] = frozenset(
    {"CrimeHeadID", "ActCode", "SectionCode"}
)
OCCUPATION_COLS: frozenset[str] = frozenset(
    {"OccupationID", "OccupationName"}
)
RELIGION_COLS: frozenset[str] = frozenset(
    {"ReligionID", "ReligionName"}
)
CASTE_COLS: frozenset[str] = frozenset(
    {"caste_master_id", "caste_master_name"}
)

# The KSP CaseMaster has a vector embedding column. The AI-generated
# SQL is unlikely to touch it, but we keep it in the allowlist so a
# hand-written "give me the vector for case N" query still validates.
CASE_MASTER_COLS: frozenset[str] = frozenset(
    {
        "CaseMasterID",
        "CrimeNo",
        "CaseNo",
        "CrimeRegisteredDate",
        "PolicePersonID",
        "PoliceStationID",
        "CaseCategoryID",
        "GravityOffenceID",
        "CrimeMajorHeadID",
        "CrimeMinorHeadID",
        "CaseStatusID",
        "CourtID",
        "IncidentFromDate",
        "IncidentToDate",
        "InfoReceivedPSDate",
        "latitude",
        "longitude",
        "BriefFacts",
        "mo_embedding",
        "is_series_crime",
        "series_id",
        "created_at",
    }
)
COMPLAINANT_COLS: frozenset[str] = frozenset(
    {
        "ComplainantID",
        "CaseMasterID",
        "ComplainantName",
        "AgeYear",
        "OccupationID",
        "ReligionID",
        "CasteID",
        "GenderID",
    }
)
VICTIM_COLS: frozenset[str] = frozenset(
    {
        "VictimMasterID",
        "CaseMasterID",
        "VictimName",
        "AgeYear",
        "GenderID",
        "VictimPolice",
        "photo_url",
        "photo_hash",
    }
)
ACCUSED_COLS: frozenset[str] = frozenset(
    {
        "AccusedMasterID",
        "CaseMasterID",
        "AccusedName",
        "AgeYear",
        "GenderID",
        "PersonID",
        "photo_url",
        "photo_hash",
        "address",
        "is_known_criminal",
        "criminal_history",
    }
)
ARREST_SURRENDER_COLS: frozenset[str] = frozenset(
    {
        "ArrestSurrenderID",
        "CaseMasterID",
        "ArrestSurrenderTypeID",
        "ArrestSurrenderDate",
        "ArrestSurrenderStateId",
        "ArrestSurrenderDistrictId",
        "PoliceStationID",
        "IOID",
        "CourtID",
        "AccusedMasterID",
        "IsAccused",
        "IsComplainantAccused",
    }
)
ACT_SECTION_ASSOC_COLS: frozenset[str] = frozenset(
    {
        "CaseMasterID",
        "ActID",
        "SectionID",
        "ActOrderID",
        "SectionOrderID",
    }
)
CHARGESHEET_COLS: frozenset[str] = frozenset(
    {
        "CSID",
        "CaseMasterID",
        "csdate",
        "cstype",
        "PolicePersonID",
    }
)
EVIDENCE_COLS: frozenset[str] = frozenset(
    {
        "EvidenceID",
        "CaseMasterID",
        "evidence_type",
        "file_url",
        "file_hash",
        "description",
        "gps_lat",
        "gps_lng",
        "collected_at",
        "uploaded_by",
        "created_at",
    }
)
RECOVERED_ITEMS_COLS: frozenset[str] = frozenset(
    {
        "RecoveryID",
        "CaseMasterID",
        "AccusedMasterID",
        "item_description",
        "quantity",
        "estimated_value",
        "photo_url",
        "photo_hash",
        "recovery_date",
        "recovery_location",
        "recovered_by",
        "witness_name",
        "seizure_memo_ref",
        "created_at",
    }
)
AUDIT_LOG_COLS: frozenset[str] = frozenset(
    {
        "LogID",
        "EmployeeID",
        "officer_name",
        "officer_rank",
        "action",
        "query_text",
        "result_count",
        "ip_address",
        "created_at",
    }
)
USERS_COLS: frozenset[str] = frozenset(
    {
        "UserID",
        "EmployeeID",
        "email",
        "role",
        "is_active",
        "last_login",
        "created_at",
    }
)


# ---------------------------------------------------------------------
# The master allowlist
# ---------------------------------------------------------------------

SCHEMA_TABLES: dict[str, frozenset[str]] = {
    "State": STATE_COLS,
    "District": DISTRICT_COLS,
    "UnitType": UNIT_TYPE_COLS,
    "Unit": UNIT_COLS,
    "Rank": RANK_COLS,
    "Designation": DESIGNATION_COLS,
    "Employee": EMPLOYEE_COLS,
    "Court": COURT_COLS,
    "CaseCategory": CASE_CATEGORY_COLS,
    "GravityOffence": GRAVITY_COLS,
    "CaseStatusMaster": CASE_STATUS_COLS,
    "CrimeHead": CRIME_HEAD_COLS,
    "CrimeSubHead": CRIME_SUB_HEAD_COLS,
    "Act": ACT_COLS,
    "Section": SECTION_COLS,
    "CrimeHeadActSection": CRIME_HEAD_ACT_SECTION_COLS,
    "OccupationMaster": OCCUPATION_COLS,
    "ReligionMaster": RELIGION_COLS,
    "CasteMaster": CASTE_COLS,
    "CaseMaster": CASE_MASTER_COLS,
    "ComplainantDetails": COMPLAINANT_COLS,
    "Victim": VICTIM_COLS,
    "Accused": ACCUSED_COLS,
    "ArrestSurrender": ARREST_SURRENDER_COLS,
    "ActSectionAssociation": ACT_SECTION_ASSOC_COLS,
    "ChargesheetDetails": CHARGESHEET_COLS,
    "Evidence": EVIDENCE_COLS,
    "RecoveredItems": RECOVERED_ITEMS_COLS,
    "AuditLog": AUDIT_LOG_COLS,
    "Users": USERS_COLS,
}


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------


def get_schema_registry() -> Mapping[str, frozenset[str]]:
    """Return the process-wide schema allowlist.

    The function is intentionally a one-liner that returns the module
    constant — but exposing it through a function gives callers
    (services, tests) a single import to mock or override.
    """
    return SCHEMA_TABLES


@lru_cache(maxsize=1)
def _cached_registry() -> Mapping[str, frozenset[str]]:
    """Cached view of the registry, in case a future hot path needs it."""
    return SCHEMA_TABLES


def get_schema_summary() -> str:
    """Return a Markdown table of every table and its columns.

    The text is injected into the ``{{SCHEMA_SUMMARY}}`` placeholder of
    :file:`backend/ai/prompts/sql_prompt.md` so the LLM sees the same
    schema the validator enforces. A drift test asserts the rendered
    output mentions every table name.
    """
    lines: list[str] = [
        "| Table | Columns |",
        "|---|---|",
    ]
    for table, cols in sorted(SCHEMA_TABLES.items()):
        lines.append(f"| `{table}` | {', '.join(f'`{c}`' for c in sorted(cols))} |")
    return "\n".join(lines)


def is_known_table(table: str) -> bool:
    """Return ``True`` if ``table`` is in the allowlist."""
    return table in SCHEMA_TABLES


def known_columns(table: str) -> frozenset[str]:
    """Return the allowlisted column set for ``table``.

    Returns an empty ``frozenset`` if the table is unknown — callers
    are expected to have already checked :func:`is_known_table`.
    """
    return SCHEMA_TABLES.get(table, frozenset())


__all__ = [
    "SCHEMA_TABLES",
    "get_schema_registry",
    "get_schema_summary",
    "is_known_table",
    "known_columns",
]
