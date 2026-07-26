"""
Schema registry — the **single source of truth** for the SQL
allowlist used by the AI investigation engine.

All table names and column names are lowercase to match the Supabase
schema exactly. The validator uses case-insensitive matching so
LLM-generated SQL with mixed case still validates correctly.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Mapping


# ---------------------------------------------------------------------
# Per-table column allowlists (all lowercase — mirrors Supabase)
# ---------------------------------------------------------------------

STATE_COLS: frozenset[str] = frozenset(
    {"stateid", "statename", "nationalityid", "active"}
)
DISTRICT_COLS: frozenset[str] = frozenset(
    {"districtid", "districtname", "stateid", "active"}
)
UNIT_TYPE_COLS: frozenset[str] = frozenset(
    {"unittypeid", "unittypename", "citydiststate", "hierarchy", "active"}
)
UNIT_COLS: frozenset[str] = frozenset(
    {
        "unitid",
        "unitname",
        "typeid",
        "parentunit",
        "stateid",
        "districtid",
        "latitude",
        "longitude",
        "active",
    }
)
RANK_COLS: frozenset[str] = frozenset(
    {"rankid", "rankname", "hierarchy", "active"}
)
DESIGNATION_COLS: frozenset[str] = frozenset(
    {"designationid", "designationname", "sortorder", "active"}
)
EMPLOYEE_COLS: frozenset[str] = frozenset(
    {
        "employeeid",
        "districtid",
        "unitid",
        "rankid",
        "designationid",
        "kgid",
        "firstname",
        "employeedob",
        "genderid",
        "bloodgroupid",
        "physicallychallenged",
        "appointmentdate",
        "active",
    }
)
COURT_COLS: frozenset[str] = frozenset(
    {"courtid", "courtname", "districtid", "stateid", "active"}
)
CASE_CATEGORY_COLS: frozenset[str] = frozenset(
    {"casecategoryid", "lookupvalue"}
)
GRAVITY_COLS: frozenset[str] = frozenset(
    {"gravityoffenceid", "lookupvalue"}
)
CASE_STATUS_COLS: frozenset[str] = frozenset(
    {"casestatusid", "casestatusname"}
)
CRIME_HEAD_COLS: frozenset[str] = frozenset(
    {"crimeheadid", "crimegroupname", "active"}
)
CRIME_SUB_HEAD_COLS: frozenset[str] = frozenset(
    {"crimesubheadid", "crimeheadid", "crimeheadname", "seqid", "active"}
)
ACT_COLS: frozenset[str] = frozenset(
    {"actcode", "actdescription", "shortname", "active"}
)
SECTION_COLS: frozenset[str] = frozenset(
    {"sectioncode", "actcode", "sectiondescription", "active"}
)
CRIME_HEAD_ACT_SECTION_COLS: frozenset[str] = frozenset(
    {"crimeheadid", "actcode", "sectioncode"}
)
OCCUPATION_COLS: frozenset[str] = frozenset(
    {"occupationid", "occupationname"}
)
RELIGION_COLS: frozenset[str] = frozenset(
    {"religionid", "religionname"}
)
CASTE_COLS: frozenset[str] = frozenset(
    {"caste_master_id", "caste_master_name"}
)
CASE_MASTER_COLS: frozenset[str] = frozenset(
    {
        "casemasterid",
        "crimeno",
        "caseno",
        "crimeregistereddate",
        "policepersonid",
        "policestationid",
        "casecategoryid",
        "gravityoffenceid",
        "crimemajorheadid",
        "crimeminorheadid",
        "casestatusid",
        "courtid",
        "incidentfromdate",
        "incidenttodate",
        "inforeceivedpsdate",
        "latitude",
        "longitude",
        "brieffacts",
        "mo_embedding",
        "is_series_crime",
        "series_id",
        "created_at",
    }
)
COMPLAINANT_COLS: frozenset[str] = frozenset(
    {
        "complainantid",
        "casemasterid",
        "complainantname",
        "ageyear",
        "occupationid",
        "religionid",
        "casteid",
        "genderid",
    }
)
VICTIM_COLS: frozenset[str] = frozenset(
    {
        "victimmasterid",
        "casemasterid",
        "victimname",
        "ageyear",
        "genderid",
        "victimpolice",
        "photo_url",
        "photo_hash",
    }
)
ACCUSED_COLS: frozenset[str] = frozenset(
    {
        "accusedmasterid",
        "casemasterid",
        "accusedname",
        "ageyear",
        "genderid",
        "personid",
        "photo_url",
        "photo_hash",
        "address",
        "is_known_criminal",
        "criminal_history",
    }
)
ARREST_SURRENDER_COLS: frozenset[str] = frozenset(
    {
        "arrestsurrenderid",
        "casemasterid",
        "arrestsurrendertypeid",
        "arrestsurrenderdate",
        "arrestsurrenderstateid",
        "arrestsurrenderdistrictid",
        "policestationid",
        "ioid",
        "courtid",
        "accusedmasterid",
        "isaccused",
        "iscomplainantaccused",
    }
)
ACT_SECTION_ASSOC_COLS: frozenset[str] = frozenset(
    {
        "casemasterid",
        "actid",
        "sectionid",
        "actorderid",
        "sectionorderid",
    }
)
CHARGESHEET_COLS: frozenset[str] = frozenset(
    {
        "csid",
        "casemasterid",
        "csdate",
        "cstype",
        "policepersonid",
    }
)
EVIDENCE_COLS: frozenset[str] = frozenset(
    {
        "evidenceid",
        "casemasterid",
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
        "recoveryid",
        "casemasterid",
        "accusedmasterid",
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
        "logid",
        "employeeid",
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
        "userid",
        "employeeid",
        "email",
        "role",
        "is_active",
        "last_login",
        "created_at",
    }
)


# ---------------------------------------------------------------------
# The master allowlist — keys are lowercase table names
# ---------------------------------------------------------------------

SCHEMA_TABLES: dict[str, frozenset[str]] = {
    "state": STATE_COLS,
    "district": DISTRICT_COLS,
    "unittype": UNIT_TYPE_COLS,
    "unit": UNIT_COLS,
    "rank": RANK_COLS,
    "designation": DESIGNATION_COLS,
    "employee": EMPLOYEE_COLS,
    "court": COURT_COLS,
    "casecategory": CASE_CATEGORY_COLS,
    "gravityoffence": GRAVITY_COLS,
    "casestatusmaster": CASE_STATUS_COLS,
    "crimehead": CRIME_HEAD_COLS,
    "crimesubhead": CRIME_SUB_HEAD_COLS,
    "act": ACT_COLS,
    "section": SECTION_COLS,
    "crimeheadactsection": CRIME_HEAD_ACT_SECTION_COLS,
    "occupationmaster": OCCUPATION_COLS,
    "religionmaster": RELIGION_COLS,
    "castemaster": CASTE_COLS,
    "casemaster": CASE_MASTER_COLS,
    "complainantdetails": COMPLAINANT_COLS,
    "victim": VICTIM_COLS,
    "accused": ACCUSED_COLS,
    "arrestsurrender": ARREST_SURRENDER_COLS,
    "actsectionassociation": ACT_SECTION_ASSOC_COLS,
    "chargesheetdetails": CHARGESHEET_COLS,
    "evidence": EVIDENCE_COLS,
    "recovereditems": RECOVERED_ITEMS_COLS,
    "auditlog": AUDIT_LOG_COLS,
    "users": USERS_COLS,
}


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------


def get_schema_registry() -> Mapping[str, frozenset[str]]:
    """Return the process-wide schema allowlist."""
    return SCHEMA_TABLES


@lru_cache(maxsize=1)
def _cached_registry() -> Mapping[str, frozenset[str]]:
    return SCHEMA_TABLES


def get_schema_summary() -> str:
    """Return a Markdown table of every table and its columns."""
    lines: list[str] = [
        "| Table | Columns |",
        "|---|---|",
    ]
    for table, cols in sorted(SCHEMA_TABLES.items()):
        lines.append(f"| `{table}` | {', '.join(f'`{c}`' for c in sorted(cols))} |")
    return "\n".join(lines)


def is_known_table(table: str) -> bool:
    """Return ``True`` if ``table`` is in the allowlist (case-insensitive)."""
    return table.lower() in SCHEMA_TABLES


def known_columns(table: str) -> frozenset[str]:
    """Return the allowlisted column set for ``table``."""
    return SCHEMA_TABLES.get(table.lower(), frozenset())


__all__ = [
    "SCHEMA_TABLES",
    "get_schema_registry",
    "get_schema_summary",
    "is_known_table",
    "known_columns",
]
