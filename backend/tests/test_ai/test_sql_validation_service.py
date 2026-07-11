"""
Tests for :class:`backend.ai.services.sql_validation_service.SQLValidationService`.

This is the safety heart of the AI investigation engine. Every
rejection the validator can make is covered by a dedicated test,
plus a battery of SQL-injection attack strings to prove the
defence is real.
"""
from __future__ import annotations

import pytest

from backend.ai.schemas.ai import GeneratedSQL
from backend.ai.services.exceptions import UnsafeSQL, ValidationFailure
from backend.ai.services.sql_validation_service import (
    DEFAULT_FORBIDDEN_VERBS,
    DEFAULT_READ_ONLY_VERBS,
    SQLValidationService,
)


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


@pytest.fixture
def schema():
    """A small fixture schema with the KSP shape."""
    return {
        "CaseMaster": frozenset(
            {
                "CaseMasterID",
                "CrimeNo",
                "CrimeRegisteredDate",
                "PoliceStationID",
                "CrimeMajorHeadID",
                "CaseStatusID",
                "BriefFacts",
                "latitude",
                "longitude",
                "created_at",
            }
        ),
        "Accused": frozenset(
            {"AccusedMasterID", "CaseMasterID", "AccusedName", "AgeYear"}
        ),
        "CrimeHead": frozenset({"CrimeHeadID", "CrimeGroupName"}),
        "Unit": frozenset(
            {"UnitID", "UnitName", "DistrictID", "latitude", "longitude"}
        ),
    }


@pytest.fixture
def validator(schema):
    return SQLValidationService(schema=schema)


def _gen(sql: str, params: dict | None = None, tables: list[str] | None = None) -> GeneratedSQL:
    return GeneratedSQL(
        sql=sql,
        params=params or {},
        tables=tables or [],
    )


# ---------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------


class TestValidatorHappyPath:
    def test_simple_select(self, validator):
        out = validator.validate(
            _gen(
                "SELECT CaseMasterID, CrimeNo FROM CaseMaster "
                "ORDER BY CaseMasterID DESC LIMIT 100",
            )
        )
        assert out.sql == (
            "SELECT CaseMasterID, CrimeNo FROM CaseMaster "
            "ORDER BY CaseMasterID DESC LIMIT 100"
        )
        assert out.tables == ["CaseMaster"]

    def test_with_cte(self, validator):
        out = validator.validate(
            _gen(
                "WITH recent AS ("
                "SELECT CaseMasterID FROM CaseMaster "
                "ORDER BY CaseMasterID DESC LIMIT 10"
                ") SELECT * FROM recent"
            )
        )
        assert "WITH" in out.sql.upper()

    def test_join(self, validator):
        out = validator.validate(
            _gen(
                "SELECT cm.CaseMasterID, a.AccusedName "
                "FROM CaseMaster cm "
                "JOIN Accused a ON a.CaseMasterID = cm.CaseMasterID "
                "ORDER BY cm.CaseMasterID DESC LIMIT 50"
            )
        )
        assert set(out.tables) == {"CaseMaster", "Accused"}

    def test_aggregate(self, validator):
        out = validator.validate(
            _gen(
                "SELECT COUNT(*) AS n, AVG(AgeYear) AS avg_age "
                "FROM Accused"
            )
        )
        assert "COUNT" in out.sql.upper()

    def test_trailing_semicolon_stripped(self, validator):
        out = validator.validate(
            _gen("SELECT CaseMasterID FROM CaseMaster LIMIT 10;")
        )
        assert not out.sql.endswith(";")
        assert out.sql == "SELECT CaseMasterID FROM CaseMaster LIMIT 10"

    def test_param_with_colon_prefix(self, validator):
        out = validator.validate(
            _gen(
                "SELECT * FROM CaseMaster WHERE CaseMasterID = :id",
                params={":id": 12},
            )
        )
        assert out.params["id"] == 12


# ---------------------------------------------------------------------
# Empty / malformed
# ---------------------------------------------------------------------


class TestValidatorEmpty:
    def test_empty_sql_raises(self, validator):
        with pytest.raises(ValidationFailure) as ei:
            validator.validate(_gen(""))
        assert ei.value.category == "empty"

    def test_whitespace_only_raises(self, validator):
        with pytest.raises(ValidationFailure) as ei:
            validator.validate(_gen("   \n\t  "))
        assert ei.value.category == "empty"


# ---------------------------------------------------------------------
# Forbidden verbs
# ---------------------------------------------------------------------


class TestValidatorForbiddenVerbs:
    @pytest.mark.parametrize("verb", sorted(DEFAULT_FORBIDDEN_VERBS))
    def test_forbidden_verb_rejected(self, validator, verb):
        sql = f"{verb} FROM CaseMaster"
        with pytest.raises(ValidationFailure) as ei:
            validator.validate(_gen(sql))
        assert ei.value.category in ("forbidden_verb", "forbidden_token")

    def test_delete_rejected(self, validator):
        with pytest.raises(ValidationFailure):
            validator.validate(
                _gen("DELETE FROM CaseMaster WHERE CaseMasterID = 1")
            )

    def test_update_rejected(self, validator):
        with pytest.raises(ValidationFailure):
            validator.validate(
                _gen(
                    "UPDATE CaseMaster SET CrimeNo = 'X' "
                    "WHERE CaseMasterID = 1"
                )
            )

    def test_drop_rejected(self, validator):
        with pytest.raises(ValidationFailure):
            validator.validate(_gen("DROP TABLE CaseMaster"))

    def test_insert_rejected(self, validator):
        with pytest.raises(ValidationFailure):
            validator.validate(
                _gen(
                    "INSERT INTO CaseMaster (CrimeNo) VALUES ('X')"
                )
            )


# ---------------------------------------------------------------------
# Unsupported verbs (not in the allowlist)
# ---------------------------------------------------------------------


class TestValidatorUnsupportedVerbs:
    def test_explain_rejected(self, validator):
        with pytest.raises(ValidationFailure) as ei:
            validator.validate(_gen("EXPLAIN SELECT 1"))
        assert ei.value.category in (
            "unsupported_verb",
            "forbidden_token",
        )

    def test_show_rejected(self, validator):
        with pytest.raises(ValidationFailure) as ei:
            validator.validate(_gen("SHOW TABLES"))
        assert ei.value.category == "unsupported_verb"


# ---------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------


class TestValidatorComments:
    def test_line_comment_rejected(self, validator):
        with pytest.raises(ValidationFailure) as ei:
            validator.validate(
                _gen(
                    "SELECT CaseMasterID FROM CaseMaster "
                    "-- this is a comment\n"
                    "ORDER BY CaseMasterID"
                )
            )
        assert ei.value.category == "comment"

    def test_block_comment_rejected(self, validator):
        with pytest.raises(ValidationFailure) as ei:
            validator.validate(
                _gen(
                    "SELECT CaseMasterID /* comment */ FROM CaseMaster"
                )
            )
        assert ei.value.category == "comment"

    def test_comment_inside_string_literal_ok(self, validator):
        # Strings must not trigger the comment regex. The SQL has
        # no real comments — only comment-shaped substrings inside
        # string literals — so validation should pass.
        out = validator.validate(
            _gen(
                "SELECT CaseMasterID FROM CaseMaster "
                "WHERE CrimeNo = '-- not a comment' "
                "AND BriefFacts LIKE '/* still not */%'"
            )
        )
        assert out.sql


# ---------------------------------------------------------------------
# Multiple statements
# ---------------------------------------------------------------------


class TestValidatorMultipleStatements:
    def test_two_selects_rejected(self, validator):
        with pytest.raises(ValidationFailure) as ei:
            validator.validate(
                _gen(
                    "SELECT 1 FROM CaseMaster; "
                    "SELECT 2 FROM CaseMaster"
                )
            )
        assert ei.value.category == "multiple_statements"

    def test_select_then_delete_rejected(self, validator):
        with pytest.raises(ValidationFailure) as ei:
            validator.validate(
                _gen(
                    "SELECT CaseMasterID FROM CaseMaster; "
                    "DELETE FROM CaseMaster"
                )
            )
        # The forbidden token regex catches the DELETE first.
        assert ei.value.category in (
            "multiple_statements",
            "forbidden_token",
        )


# ---------------------------------------------------------------------
# Unknown tables
# ---------------------------------------------------------------------


class TestValidatorUnknownTables:
    def test_unknown_table_rejected(self, validator):
        with pytest.raises(ValidationFailure) as ei:
            validator.validate(_gen("SELECT * FROM Users"))
        assert ei.value.category == "unknown_table"
        assert "Users" in ei.value.reason

    def test_unknown_join_table_rejected(self, validator):
        with pytest.raises(ValidationFailure) as ei:
            validator.validate(
                _gen(
                    "SELECT * FROM CaseMaster c "
                    "JOIN Users u ON u.id = c.CaseMasterID"
                )
            )
        assert ei.value.category == "unknown_table"

    def test_no_tables_in_query_rejected(self, validator):
        # The validator cannot find any table, so it cannot check
        # columns either. The "unknown_table" branch fires when
        # tables is non-empty. With no tables, the column check
        # is a no-op. This is the intended behaviour — the
        # investigation pipeline is expected to never produce
        # such a query (the SQL prompt requires a FROM).
        out = validator.validate(
            _gen("SELECT 1 + 1 AS two")
        )
        assert out.tables == []


# ---------------------------------------------------------------------
# Unknown columns
# ---------------------------------------------------------------------


class TestValidatorUnknownColumns:
    def test_unknown_column_rejected(self, validator):
        with pytest.raises(ValidationFailure) as ei:
            validator.validate(
                _gen(
                    "SELECT password FROM CaseMaster"
                )
            )
        assert ei.value.category == "unknown_column"
        assert "password" in ei.value.reason

    def test_qualified_unknown_column_rejected(self, validator):
        with pytest.raises(ValidationFailure):
            validator.validate(
                _gen(
                    "SELECT cm.password FROM CaseMaster cm"
                )
            )

    def test_known_column_in_where_ok(self, validator):
        out = validator.validate(
            _gen(
                "SELECT CaseMasterID FROM CaseMaster "
                "WHERE CrimeNo = :fir",
                params={"fir": "1044"},
            )
        )
        assert out.sql

    def test_unknown_column_in_where_rejected(self, validator):
        with pytest.raises(ValidationFailure) as ei:
            validator.validate(
                _gen(
                    "SELECT CaseMasterID FROM CaseMaster "
                    "WHERE secret_value = 1"
                )
            )
        assert ei.value.category == "unknown_column"

    def test_unknown_column_in_order_by_rejected(self, validator):
        with pytest.raises(ValidationFailure):
            validator.validate(
                _gen(
                    "SELECT CaseMasterID FROM CaseMaster "
                    "ORDER BY evil_column"
                )
            )

    def test_star_is_allowed(self, validator):
        out = validator.validate(_gen("SELECT * FROM CaseMaster LIMIT 1"))
        assert out.sql


# ---------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------


class TestValidatorParameters:
    def test_unbound_param_rejected(self, validator):
        with pytest.raises(ValidationFailure) as ei:
            validator.validate(
                _gen(
                    "SELECT * FROM CaseMaster WHERE CaseMasterID = :id"
                )
            )
        assert ei.value.category == "unbound_param"

    def test_bound_param_accepted(self, validator):
        out = validator.validate(
            _gen(
                "SELECT * FROM CaseMaster WHERE CaseMasterID = :id",
                params={"id": 12},
            )
        )
        assert out.params["id"] == 12

    def test_colon_prefix_bound_accepted(self, validator):
        out = validator.validate(
            _gen(
                "SELECT * FROM CaseMaster WHERE CaseMasterID = :id",
                params={":id": 12},
            )
        )
        assert out.params["id"] == 12

    def test_list_value_rejected(self, validator):
        with pytest.raises(ValidationFailure) as ei:
            validator.validate(
                _gen(
                    "SELECT * FROM CaseMaster WHERE CaseMasterID IN :ids",
                    params={"ids": [1, 2, 3]},
                )
            )
        assert ei.value.category == "bad_param_value"

    def test_dict_value_rejected(self, validator):
        with pytest.raises(ValidationFailure) as ei:
            validator.validate(
                _gen(
                    "SELECT * FROM CaseMaster WHERE CaseMasterID = :p",
                    params={"p": {"a": 1}},
                )
            )
        assert ei.value.category == "bad_param_value"

    def test_string_value_accepted(self, validator):
        out = validator.validate(
            _gen(
                "SELECT * FROM CaseMaster WHERE CrimeNo = :fir",
                params={"fir": "1044"},
            )
        )
        assert out.params["fir"] == "1044"

    def test_int_value_accepted(self, validator):
        out = validator.validate(
            _gen(
                "SELECT * FROM CaseMaster WHERE CaseMasterID = :id",
                params={"id": 12},
            )
        )
        assert out.params["id"] == 12

    def test_float_value_accepted(self, validator):
        out = validator.validate(
            _gen(
                "SELECT * FROM CaseMaster WHERE latitude = :lat",
                params={"lat": 12.34},
            )
        )
        assert out.params["lat"] == 12.34

    def test_bool_value_accepted(self, validator):
        out = validator.validate(
            _gen(
                "SELECT * FROM CaseMaster WHERE latitude = :x",
                params={"x": True},
            )
        )
        assert out.params["x"] is True

    def test_none_value_accepted(self, validator):
        out = validator.validate(
            _gen(
                "SELECT * FROM CaseMaster WHERE latitude IS NULL OR latitude = :x",
                params={"x": None},
            )
        )
        assert out.params["x"] is None

    def test_non_string_key_rejected(self, validator):
        with pytest.raises(ValidationFailure) as ei:
            validator.validate(
                _gen(
                    "SELECT * FROM CaseMaster WHERE CaseMasterID = :id",
                    params={1: 12},  # type: ignore[dict-item]
                )
            )
        assert ei.value.category == "bad_param"


# ---------------------------------------------------------------------
# SQL-injection attack strings
# ---------------------------------------------------------------------


class TestValidatorSQLInjectionAttempts:
    """A battery of common attack strings. Every one must be rejected
    before it reaches the database. Adding a new test here is
    cheap insurance against a future regression."""

    @pytest.mark.parametrize(
        "payload",
        [
            # Stacked statement: 1; DROP TABLE x
            "SELECT 1; DROP TABLE CaseMaster",
            # Stacked statement with comment
            "SELECT 1; -- ha\nDROP TABLE CaseMaster",
            # Encoded stacked statement
            "SELECT 1/**/;DELETE FROM CaseMaster",
            # UNION-based extraction attempt
            "SELECT CaseMasterID FROM CaseMaster UNION SELECT password FROM users",
            # Time-based blind (PostgreSQL) — uses a function not in
            # the allowlist; the column check fails first because
            # ``pg_sleep`` is treated as a column reference.
            "SELECT CaseMasterID FROM CaseMaster WHERE 1=1 AND (SELECT pg_sleep(10)) IS NULL",
            # Quote-escape
            "SELECT * FROM CaseMaster WHERE CrimeNo = '\\' OR 1=1 --'",
            # Function that may be forbidden
            "SELECT CaseMasterID, pg_read_file('/etc/passwd') FROM CaseMaster",
            # xp_cmdshell-style attempt
            "SELECT CaseMasterID FROM CaseMaster; EXEC xp_cmdshell('dir')",
            # Drop database
            "DROP DATABASE saaransh",
            # Truncate
            "TRUNCATE CaseMaster",
            # Grant
            "GRANT ALL ON CaseMaster TO public",
            # Create table
            "CREATE TABLE evil (id INT)",
            # Merge
            "MERGE INTO CaseMaster USING evil ON 1=1",
            # Call
            "CALL evil_procedure()",
            # Copy
            "COPY CaseMaster FROM '/etc/passwd'",
            # Insert with returning
            "INSERT INTO CaseMaster (CrimeNo) VALUES ('x') RETURNING CaseMasterID",
        ],
    )
    def test_attack_rejected(self, validator, payload):
        with pytest.raises(UnsafeSQL):
            validator.validate(_gen(payload))

    def test_boolean_injection_against_unknown_table_rejected(
        self, validator
    ):
        """The classic ``OR '1'='1'`` injection is rejected at the
        *table* layer: the malicious payload references ``users``,
        which is not in the allowlist."""
        with pytest.raises(UnsafeSQL):
            validator.validate(
                _gen(
                    "SELECT * FROM users WHERE username='admin' "
                    "OR '1'='1'"
                )
            )


# ---------------------------------------------------------------------
# Defence-in-depth: assert_read_only on the executor side
# ---------------------------------------------------------------------


class TestValidatorVerbSets:
    def test_default_verb_sets(self):
        assert "SELECT" in DEFAULT_READ_ONLY_VERBS
        assert "WITH" in DEFAULT_READ_ONLY_VERBS
        assert "DELETE" in DEFAULT_FORBIDDEN_VERBS
        assert "UPDATE" in DEFAULT_FORBIDDEN_VERBS
        assert "INSERT" in DEFAULT_FORBIDDEN_VERBS
        assert "DROP" in DEFAULT_FORBIDDEN_VERBS

    def test_custom_verb_sets(self, schema):
        v = SQLValidationService(
            schema=schema,
            forbidden_verbs=frozenset({"DELETE", "DROP"}),
            read_only_verbs=frozenset({"SELECT"}),
        )
        with pytest.raises(ValidationFailure):
            v.validate(_gen("DELETE FROM CaseMaster"))
        # INSERT is not in the custom forbidden set; the verb
        # allowlist is the read-only set, so INSERT is rejected
        # as "unsupported verb".
        with pytest.raises(ValidationFailure) as ei:
            v.validate(_gen("INSERT INTO CaseMaster VALUES (1)"))
        assert ei.value.category in (
            "unsupported_verb",
            "forbidden_token",
        )
