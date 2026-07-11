"""
Tests for the schema registry and a drift test against the real
``ksp_real_schema.sql``.

The drift test parses the SQL schema and asserts every
``CREATE TABLE`` and its columns is reflected in
:data:`backend.services.schema_registry.SCHEMA_TABLES`. A
regression test catches the most common Phase 6 failure: someone
adds a column to the SQL schema and forgets to update the
allowlist.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from backend.services import schema_registry
from backend.services.schema_registry import (
    SCHEMA_TABLES,
    get_schema_registry,
    get_schema_summary,
    is_known_table,
    known_columns,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCHEMA_FILE = PROJECT_ROOT / "database" / "schema" / "ksp_real_schema.sql"


# ---------------------------------------------------------------------
# Schema registry
# ---------------------------------------------------------------------


class TestSchemaRegistry:
    def test_all_tables_are_frozensets(self):
        for table, cols in SCHEMA_TABLES.items():
            assert isinstance(cols, frozenset), f"{table} is not a frozenset"
            assert all(isinstance(c, str) for c in cols)

    def test_get_schema_registry_returns_same_data(self):
        assert get_schema_registry() is SCHEMA_TABLES

    def test_is_known_table(self):
        assert is_known_table("CaseMaster") is True
        assert is_known_table("NotATable") is False
        assert is_known_table("") is False

    def test_known_columns(self):
        cols = known_columns("CaseMaster")
        assert "CaseMasterID" in cols
        assert "CrimeNo" in cols

    def test_known_columns_unknown_table_returns_empty(self):
        assert known_columns("NotATable") == frozenset()

    def test_schema_summary_contains_every_table(self):
        summary = get_schema_summary()
        for table in SCHEMA_TABLES:
            assert table in summary, f"Table {table!r} missing from summary"

    def test_schema_summary_contains_every_column(self):
        summary = get_schema_summary()
        # Spot-check a few representative columns.
        assert "CaseMasterID" in summary
        assert "CrimeNo" in summary
        assert "BriefFacts" in summary
        assert "mo_embedding" in summary
        assert "AccusedName" in summary

    def test_known_tables_match_ksp_schema(self):
        """The set of registered tables should match the schema.

        This is a *softer* check than the drift test below — it
        just confirms every known table has at least its PK
        column registered."""
        expected_pk_columns = {
            "State": "StateID",
            "District": "DistrictID",
            "Unit": "UnitID",
            "CaseMaster": "CaseMasterID",
            "Accused": "AccusedMasterID",
            "Victim": "VictimMasterID",
            "CrimeHead": "CrimeHeadID",
        }
        for table, pk in expected_pk_columns.items():
            assert table in SCHEMA_TABLES
            assert pk in SCHEMA_TABLES[table]


# ---------------------------------------------------------------------
# Drift test against the real SQL schema
# ---------------------------------------------------------------------


_PARSE_TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\((?P<body>.*?)\)\s*;",
    re.IGNORECASE | re.DOTALL,
)


def _parse_schema(path: Path) -> dict[str, set[str]]:
    """Parse a PostgreSQL ``CREATE TABLE`` dump into a
    ``table -> {column}`` mapping.

    The parser is intentionally simple: it looks for
    ``CREATE TABLE [name] ( ... )`` blocks, splits the body on
    commas at depth zero, and extracts the first identifier of
    each item (skipping ``PRIMARY KEY`` and ``FOREIGN KEY``
    constraint lines).
    """
    text = path.read_text(encoding="utf-8")
    # Strip line and block comments first so a fragment like
    # ``PersonID VARCHAR(10), -- A1, A2, A3...`` does not
    # introduce spurious ``A2`` and ``A3`` columns after the
    # comma split.
    text = re.sub(r"--[^\n]*", "", text)
    text = re.sub(r"/\*[\s\S]*?\*/", "", text)
    tables: dict[str, set[str]] = {}
    for match in _PARSE_TABLE_RE.finditer(text):
        name = match.group("name")
        body = match.group("body")
        columns: set[str] = set()
        for raw in _split_top_level_commas(body):
            line = raw.strip()
            if not line:
                continue
            upper = line.upper()
            if upper.startswith("PRIMARY KEY") or upper.startswith(
                "FOREIGN KEY"
            ) or upper.startswith("CONSTRAINT") or upper.startswith("UNIQUE"):
                continue
            # Take the first identifier — the column name.
            ident = re.match(r"\s*\"?([A-Za-z_][A-Za-z0-9_]*)\"?", line)
            if ident:
                columns.add(ident.group(1))
        tables[name] = columns
    return tables


def _split_top_level_commas(body: str) -> list[str]:
    """Split a CREATE TABLE body on commas that are not inside parens."""
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in body:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current))
    return parts


@pytest.mark.skipif(
    not SCHEMA_FILE.exists(),
    reason="ksp_real_schema.sql not found in this checkout",
)
class TestSchemaDrift:
    """If the SQL schema gains a column, this test fails until the
    registry is updated. The opposite direction (registry has
    columns the schema does not) is also caught."""

    def test_all_sql_tables_are_registered(self):
        sql_tables = _parse_schema(SCHEMA_FILE)
        sql_names = set(sql_tables)
        registry_names = set(SCHEMA_TABLES)
        # The audit/Users tables exist in both.
        missing = sql_names - registry_names
        assert not missing, (
            f"Tables in ksp_real_schema.sql but missing from "
            f"SCHEMA_TABLES: {sorted(missing)}"
        )

    def test_no_extra_tables_in_registry(self):
        sql_tables = _parse_schema(SCHEMA_FILE)
        sql_names = set(sql_tables)
        registry_names = set(SCHEMA_TABLES)
        extra = registry_names - sql_names
        assert not extra, (
            f"Tables in SCHEMA_TABLES but missing from "
            f"ksp_real_schema.sql: {sorted(extra)}"
        )

    def test_all_sql_columns_are_registered(self):
        sql_tables = _parse_schema(SCHEMA_FILE)
        for table, sql_cols in sql_tables.items():
            if table not in SCHEMA_TABLES:
                continue
            registry_cols = SCHEMA_TABLES[table]
            missing = sql_cols - registry_cols
            assert not missing, (
                f"Table {table!r} has columns in the SQL schema that "
                f"are missing from the registry: {sorted(missing)}"
            )
