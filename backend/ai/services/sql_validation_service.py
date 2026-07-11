"""
SQLValidationService — the safety heart of the AI investigation engine.

Every LLM-generated :class:`~backend.ai.schemas.ai.GeneratedSQL`
flows through this service before it touches the database. The
service implements the full allowlist defined in the Phase 6 spec:

  Allowed
    SELECT, WITH, GROUP BY, ORDER BY, LIMIT, COUNT, SUM, AVG, MIN, MAX

  Forbidden (reject immediately)
    DELETE, UPDATE, INSERT, ALTER, DROP, TRUNCATE, CREATE, EXEC,
    CALL, MERGE, COPY, GRANT, REVOKE

  Structural rejects
    * Multiple SQL statements (semicolons).
    * Comments (line ``--`` or block ``/* ... */``).
    * Unknown tables (table not in the schema allowlist).
    * Unknown columns (column not in the table's allowlist).
    * Un-bound parameters (``:name`` referenced in the SQL but absent
      from ``params``).
    * Non-primitive param values (lists, dicts, etc.).

  Allowed SQL
    * A single statement ending in ``;`` is allowed for the
      statement itself but the validator strips the trailing
      semicolon before parsing, so the executor receives a clean
      statement. This matches the spec ("Reject semicolons") — the
      validator interprets "reject" as "reject multi-statement", not
      "reject the trailing semicolon of a single statement".

  SELECT * guard
    * ``SELECT *`` and ``SELECT table.*`` are allowed only when the
      referenced tables exist. The spec does not forbid ``*``; the
      column allowlist is consulted for every non-``*`` reference.

The service is **stateless** and **pure-Python** — it does not
import ``sqlalchemy`` or the database layer. The schema allowlist
is passed in as a ``Mapping[str, frozenset[str]]`` so tests can use
a small fixture.

Why a hand-rolled validator instead of ``sqlglot`` or ``sqlparse``?

We need to reject a small, well-defined list of failures and we
need the rejection reason to be specific. ``sqlglot`` and
``sqlparse`` would give us a full AST, but a malicious payload can
hide a forbidden verb inside an identifier ("users; DROP TABLE x")
and a hand-rolled tokeniser catches it more reliably than a parser
that may or may not run against untrusted input. The validation
steps below are deliberately small and each maps to a documented
``UnsafeSQL.category`` value.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Iterable, Mapping, Sequence

from backend.ai.schemas.ai import (
    ALLOWED_SQL_VERBS,
    GeneratedSQL,
    ValidatedSQL,
)
from backend.ai.services.exceptions import (
    UnsafeSQL,
    ValidationFailure,
)


#: Default forbidden SQL verbs (matches the executor's allowlist).
DEFAULT_FORBIDDEN_VERBS: frozenset[str] = frozenset(
    {
        "DELETE",
        "UPDATE",
        "INSERT",
        "ALTER",
        "DROP",
        "TRUNCATE",
        "CREATE",
        "EXEC",
        "CALL",
        "MERGE",
        "COPY",
        "GRANT",
        "REVOKE",
    }
)

#: Default read-only verbs.
DEFAULT_READ_ONLY_VERBS: frozenset[str] = frozenset({"SELECT", "WITH"})

#: Tokens that, in any position, are evidence of an injection attempt.
#: Caught before the rest of the pipeline so an LLM that hallucinates
#: one of these cannot slip past the verb allowlist.
DEFAULT_FORBIDDEN_TOKENS: frozenset[str] = frozenset(
    {
        "DELETE",
        "UPDATE",
        "INSERT",
        "ALTER",
        "DROP",
        "TRUNCATE",
        "CREATE",
        "EXEC",
        "CALL",
        "MERGE",
        "COPY",
        "GRANT",
        "REVOKE",
    }
)

#: Whitelist of aggregate / clause keywords that are allowed in a
#: read-only query body. The validator checks for the **presence**
#: of these as standalone tokens — they do not by themselves grant
#: permission (the verb allowlist does), but they are explicitly
#: permitted so the documentation matches the code.
ALLOWED_CLAUSE_TOKENS: frozenset[str] = frozenset(
    {
        "SELECT",
        "FROM",
        "WHERE",
        "GROUP",
        "BY",
        "ORDER",
        "LIMIT",
        "OFFSET",
        "HAVING",
        "JOIN",
        "INNER",
        "LEFT",
        "RIGHT",
        "OUTER",
        "FULL",
        "CROSS",
        "ON",
        "AS",
        "AND",
        "OR",
        "NOT",
        "IN",
        "IS",
        "NULL",
        "LIKE",
        "ILIKE",
        "BETWEEN",
        "EXISTS",
        "DISTINCT",
        "CASE",
        "WHEN",
        "THEN",
        "ELSE",
        "END",
        "UNION",
        "INTERSECT",
        "EXCEPT",
        "WITH",
        "RECURSIVE",
        "ASC",
        "DESC",
        "COUNT",
        "SUM",
        "AVG",
        "MIN",
        "MAX",
    }
)

# Pre-compiled patterns ----------------------------------------------------

#: ``INSERT|UPDATE|...`` anywhere in the query (case-insensitive, word
#: boundary). Cheap pre-filter that runs before tokenisation.
_RE_FORBIDDEN_TOKEN = re.compile(
    r"\b(" + "|".join(DEFAULT_FORBIDDEN_TOKENS) + r")\b",
    re.IGNORECASE,
)

# Word boundary on a token like DELETE; the (?i) flag is implicit in
# the call sites via re.IGNORECASE.
_IDENTIFIER = r"[A-Za-z_][A-Za-z0-9_]*"
_STRING_LITERAL = r"'(?:''|[^'])*'"
_LINE_COMMENT = r"--[^\n]*"
_BLOCK_COMMENT = r"/\*[\s\S]*?\*/"
# A "name" used in a parameter binding: ``:district_id``.
_PARAM_REF = r":([A-Za-z_][A-Za-z0-9_]*)"

_RE_LINE_COMMENT = re.compile(_LINE_COMMENT)
_RE_BLOCK_COMMENT = re.compile(_BLOCK_COMMENT)
_RE_STRING_LITERAL = re.compile(_STRING_LITERAL)
_RE_PARAM_REF = re.compile(_PARAM_REF)
_RE_WHITESPACE = re.compile(r"\s+")
_RE_SEMICOLON = re.compile(r";")
_RE_WORD = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b")

#: SELECT ... FROM <table>[ AS alias][, <table>[ AS alias]]*
#: Captures the table identifier (unquoted). The list is iterated
#: over a much simpler pattern in real SQL; we use a broad regex
#: that captures identifiers that are not inside a string literal.
_RE_FROM_TABLE = re.compile(
    r"\bFROM\s+((?:" + _IDENTIFIER + r")(?:\s+(?:AS\s+)?(?:" + _IDENTIFIER + r"))?)",
    re.IGNORECASE,
)
_RE_JOIN_TABLE = re.compile(
    r"\bJOIN\s+(" + _IDENTIFIER + r")(?:\s+(?:AS\s+)?" + _IDENTIFIER + r")?",
    re.IGNORECASE,
)


class SQLValidationService:
    """Allowlist-based SQL validator.

    Args:
        schema: Mapping of ``table -> frozenset[column]``. Defaults
            to :data:`backend.services.schema_registry.SCHEMA_TABLES`.
            Tests can pass a smaller fixture.
        forbidden_verbs: Set of verbs to reject. Defaults to
            :data:`DEFAULT_FORBIDDEN_VERBS`.
        read_only_verbs: Set of verbs that are allowed. Defaults to
            :data:`DEFAULT_READ_ONLY_VERBS`.
        logger: Optional :class:`logging.Logger`.
    """

    def __init__(
        self,
        schema: Mapping[str, frozenset[str]] | None = None,
        *,
        forbidden_verbs: frozenset[str] = DEFAULT_FORBIDDEN_VERBS,
        read_only_verbs: frozenset[str] = DEFAULT_READ_ONLY_VERBS,
        logger: logging.Logger | None = None,
    ) -> None:
        self._schema = dict(schema) if schema is not None else _default_schema()
        self._forbidden_verbs = frozenset(s.upper() for s in forbidden_verbs)
        self._read_only_verbs = frozenset(s.upper() for s in read_only_verbs)
        self._logger = logger or logging.getLogger(
            "backend.ai.services.sql_validation_service"
        )

    # ------------------------------------------------------------------
    # Public surface
    # ------------------------------------------------------------------

    def validate(self, generated: GeneratedSQL) -> ValidatedSQL:
        """Run the full allowlist check on ``generated``.

        Args:
            generated: The output of
                :class:`~backend.ai.services.sql_generation_service.SQLGenerationService`.

        Returns:
            A :class:`ValidatedSQL` ready to hand to the executor.

        Raises:
            :class:`UnsafeSQL` (and its :class:`ValidationFailure`
                subclass): any rejection. The exception's
                ``category`` attribute identifies the step that
                failed.
        """
        sql = (generated.sql or "").strip()
        if not sql:
            raise ValidationFailure(
                "SQL is empty.",
                sql=sql,
                category="empty",
            )

        normalised = self._normalise_whitespace(sql)
        self._check_no_comments(normalised)
        self._check_no_multiple_statements(normalised)
        self._check_no_forbidden_token(normalised)
        self._check_verb(normalised)
        referenced_tables = self._extract_referenced_tables(normalised)
        self._check_known_tables(referenced_tables)
        self._check_columns(normalised, referenced_tables)
        self._check_params(normalised, generated.params)

        # Normalise the params keys: strip a leading ':' so callers
        # can pass either form to SQLAlchemy.
        normalised_params = {
            (k.lstrip(":") if isinstance(k, str) else k): v
            for k, v in (generated.params or {}).items()
        }
        return ValidatedSQL(
            sql=normalised,
            params=normalised_params,
            tables=sorted(referenced_tables),
            estimated_rows=generated.estimated_rows,
            notes=generated.notes,
        )

    # ------------------------------------------------------------------
    # Validation steps
    # ------------------------------------------------------------------

    def _normalise_whitespace(self, sql: str) -> str:
        """Collapse whitespace; strip a single trailing semicolon."""
        cleaned = _RE_WHITESPACE.sub(" ", sql).strip()
        if cleaned.endswith(";"):
            cleaned = cleaned[:-1].rstrip()
        return cleaned

    def _check_no_comments(self, sql: str) -> None:
        """Reject ``--`` line comments and ``/* ... */`` block comments."""
        # Strip string literals first so a semicolon or comment-like
        # substring inside a string cannot trigger a false positive.
        without_strings = _RE_STRING_LITERAL.sub("''", sql)
        if _RE_LINE_COMMENT.search(without_strings):
            raise ValidationFailure(
                "SQL contains a line comment (--).",
                sql=sql,
                category="comment",
            )
        if _RE_BLOCK_COMMENT.search(without_strings):
            raise ValidationFailure(
                "SQL contains a block comment (/* ... */).",
                sql=sql,
                category="comment",
            )

    def _check_no_multiple_statements(self, sql: str) -> None:
        """Reject any embedded semicolons (multi-statement attacks).

        The trailing semicolon has already been stripped by
        :meth:`_normalise_whitespace`. Any remaining ``;`` means
        the statement is one of many.
        """
        if _RE_SEMICOLON.search(sql):
            raise ValidationFailure(
                "SQL contains a semicolon; multiple statements are not allowed.",
                sql=sql,
                category="multiple_statements",
            )

    def _check_no_forbidden_token(self, sql: str) -> None:
        """Reject any forbidden verb appearing as a token.

        This runs *before* :meth:`_check_verb` so an LLM that smuggles
        ``DELETE`` into a CTE name still fails. The check ignores
        matches inside string literals.
        """
        without_strings = _RE_STRING_LITERAL.sub("''", sql)
        match = _RE_FORBIDDEN_TOKEN.search(without_strings)
        if match:
            raise ValidationFailure(
                f"SQL contains the forbidden token {match.group(0).upper()!r}.",
                sql=sql,
                category="forbidden_token",
            )

    def _check_verb(self, sql: str) -> None:
        """Reject anything that does not start with a read-only verb.

        Strips a leading ``WITH`` so ``WITH x AS (...) SELECT ...``
        is correctly classified as a read query.
        """
        first = _first_significant_token(sql)
        if not first:
            raise ValidationFailure(
                "SQL has no recognisable leading verb.",
                sql=sql,
                category="missing_verb",
            )
        if first in self._forbidden_verbs:
            raise ValidationFailure(
                f"SQL starts with forbidden verb {first!r}.",
                sql=sql,
                category="forbidden_verb",
            )
        if first not in self._read_only_verbs:
            raise ValidationFailure(
                f"SQL starts with unsupported verb {first!r}; "
                f"only {sorted(self._read_only_verbs)} are allowed.",
                sql=sql,
                category="unsupported_verb",
            )

    def _extract_referenced_tables(self, sql: str) -> set[str]:
        """Return the set of table names referenced in the query.

        The extraction ignores string literals and uses a small,
        transparent regex pair. The trade-off vs a full parser is
        a slightly broader match on edge cases (e.g. aliased
        sub-selects) but every name we collect still has to pass
        the allowlist in :meth:`_check_known_tables`, so a false
        positive just costs one extra rejection.
        """
        without_strings = _RE_STRING_LITERAL.sub("''", sql)
        # Collect CTE names introduced by WITH so we can ignore them
        # in the FROM / JOIN scan.
        cte_names = self._extract_cte_names(without_strings)
        tables: set[str] = set()
        for match in _RE_FROM_TABLE.finditer(without_strings):
            head = match.group(1).split()[0]
            if head and head not in cte_names:
                tables.add(head)
        for match in _RE_JOIN_TABLE.finditer(without_strings):
            head = match.group(1)
            if head and head not in cte_names:
                tables.add(head)
        return tables

    def _extract_table_aliases(self, sql: str) -> set[str]:
        """Return the set of aliases used in FROM/JOIN clauses.

        ``FROM CaseMaster cm`` introduces the alias ``cm``;
        ``JOIN Accused a ON ...`` introduces ``a``. These are
        used as column qualifiers (``cm.CaseMasterID``) and must
        not be treated as unknown column names.
        """
        aliases: set[str] = set()
        # FROM <table>[ AS] <alias>
        for match in re.finditer(
            r"\bFROM\s+" + _IDENTIFIER + r"(?:\s+(?:AS\s+)?(" + _IDENTIFIER + r"))?",
            sql,
            re.IGNORECASE,
        ):
            alias = match.group(1)
            if alias and alias.upper() not in {
                "WHERE", "GROUP", "ORDER", "LIMIT", "HAVING",
                "UNION", "INTERSECT", "EXCEPT",
            }:
                aliases.add(alias)
        # JOIN <table>[ AS] <alias>
        for match in re.finditer(
            r"\bJOIN\s+" + _IDENTIFIER + r"(?:\s+(?:AS\s+)?(" + _IDENTIFIER + r"))?",
            sql,
            re.IGNORECASE,
        ):
            alias = match.group(1)
            if alias and alias.upper() not in {
                "ON", "WHERE", "USING",
            }:
                aliases.add(alias)
        return aliases

    @staticmethod
    def _extract_cte_names(sql: str) -> set[str]:
        """Return the set of names introduced by a leading ``WITH`` clause.

        ``WITH x AS (... ) SELECT ...`` introduces ``x``; we must
        not treat later references to ``x`` as unknown tables.
        """
        match = re.match(
            r"^\s*WITH\b\s+(.+)$",
            sql,
            re.IGNORECASE | re.DOTALL,
        )
        if not match:
            return set()
        body = match.group(1)
        # The CTE names appear as a comma-separated list before the
        # first SELECT (or first AS). Each name is followed by an
        # optional column list and ``AS (...)``.
        names: set[str] = set()
        # The first SELECT marks the end of the CTE preamble.
        preamble_end = re.search(r"\bSELECT\b", body, re.IGNORECASE)
        if preamble_end is None:
            return set()
        preamble = body[: preamble_end.start()]
        # Split on commas that are not inside parens.
        depth = 0
        current: list[str] = []
        parts: list[str] = []
        for ch in preamble:
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
        for part in parts:
            tokens = part.strip().split()
            if tokens:
                names.add(tokens[0])
        return names

    @staticmethod
    def _extract_aliases(projection: str) -> set[str]:
        """Return the set of alias names introduced in a SELECT projection.

        Recognises the patterns ``<expr> AS <name>`` and
        ``<expr> <name>`` (an unquoted alias immediately following
        an expression). The alias is what comes after ``AS`` (or
        the last identifier in the projection item).
        """
        aliases: set[str] = set()
        if not projection:
            return aliases
        # Strip the leading SELECT keyword.
        body = re.sub(r"^\s*SELECT\b", "", projection, count=1, flags=re.IGNORECASE)
        # Walk through the projection items, split on commas at
        # depth zero.
        depth = 0
        current: list[str] = []
        parts: list[str] = []
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
        for part in parts:
            text = part.strip()
            if not text:
                continue
            # ``EXPR AS ALIAS`` form.
            as_match = re.search(
                r"\bAS\s+(\"?[A-Za-z_][A-Za-z0-9_]*\"?)",
                text,
                re.IGNORECASE,
            )
            if as_match:
                aliases.add(as_match.group(1).strip('"'))
                continue
            # ``EXPR ALIAS`` form: take the last token.
            tokens = text.split()
            if len(tokens) >= 2:
                aliases.add(tokens[-1].strip('"'))
        return aliases

    def _check_known_tables(self, tables: Iterable[str]) -> None:
        """Reject any table not in the allowlist."""
        unknown = sorted(t for t in tables if t not in self._schema)
        if unknown:
            raise ValidationFailure(
                f"SQL references unknown table(s): {unknown}. "
                f"Allowed tables: {sorted(self._schema)}.",
                sql=None,
                category="unknown_table",
            )

    def _check_columns(
        self,
        sql: str,
        referenced_tables: Sequence[str],
    ) -> None:
        """Reject any column reference not in the table's allowlist.

        The check is conservative: every identifier that appears in
        the SELECT list or in a ``WHERE``/``ORDER BY`` clause is
        compared against the union of all referenced tables'
        allowlisted columns. Identifiers that look like SQL keywords,
        literal numbers, parameter names (``:foo``), or string
        literals are skipped.
        """
        if not referenced_tables:
            return
        allowed_columns: set[str] = set()
        for table in referenced_tables:
            allowed_columns.update(self._schema.get(table, frozenset()))

        # Strip string literals and parameters, then tokenise.
        cleaned = _RE_STRING_LITERAL.sub("''", sql)
        cleaned = _RE_PARAM_REF.sub("", cleaned)

        # Skip the FROM/JOIN identifiers themselves — they are
        # already validated by _check_known_tables.
        for table in referenced_tables:
            cleaned = re.sub(
                r"\b" + re.escape(table) + r"\b", "TABLE", cleaned
            )

        # Find the SELECT projection and the WHERE clause. Anything
        # outside those two positions is a JOIN, an alias, or a
        # table reference and is not a column.
        projection, where, order = _split_select_where_order(cleaned)

        # Collect aliases (anything after AS) so we don't treat them
        # as column names. Aliases are introduced by ``<expr> AS
        # <name>`` in the SELECT projection.
        aliases = self._extract_aliases(projection)
        # Table aliases (FROM CaseMaster cm) used as column
        # qualifiers (cm.CaseMasterID) must not be treated as
        # columns either.
        table_aliases = self._extract_table_aliases(sql)
        # CTE names introduced by a WITH clause and referenced
        # later (``SELECT * FROM cte``) are not columns.
        cte_names = self._extract_cte_names(sql)

        candidates = set()
        candidates.update(_extract_identifiers(projection))
        candidates.update(_extract_identifiers(where))
        candidates.update(_extract_identifiers(order))

        # Drop SQL keywords, the placeholder ``*``, and the literal
        # numbers / parameter substitutes.
        allowed_columns_upper = {c.upper() for c in allowed_columns}
        unknown = sorted(
            c
            for c in candidates
            if c
            and c != "*"
            and c.upper() not in ALLOWED_CLAUSE_TOKENS
            and c.upper() not in {"NULL", "TRUE", "FALSE"}
            and c.upper() not in {t.upper() for t in self._schema}
            and c.upper() not in {t.upper() for t in referenced_tables}
            and c.upper() not in {a.upper() for a in aliases}
            and c.upper() not in {a.upper() for a in table_aliases}
            and c.upper() not in {n.upper() for n in cte_names}
            and c.upper() not in allowed_columns_upper
            and not c.isdigit()
        )
        if unknown:
            raise ValidationFailure(
                f"SQL references unknown column(s): {unknown}. "
                f"Allowed columns for "
                f"{sorted(referenced_tables)}: "
                f"{sorted(allowed_columns)}.",
                sql=sql,
                category="unknown_column",
            )

    def _check_params(
        self,
        sql: str,
        params: Mapping[str, Any] | None,
    ) -> None:
        """Reject any unbound parameter or non-primitive value."""
        # Find every :name in the SQL.
        names = {m.group(1) for m in _RE_PARAM_REF.finditer(sql)}
        bound = dict(params or {})

        # Normalise keys (drop leading colon) so :foo and foo are
        # interchangeable.
        bound_normalised: dict[str, Any] = {}
        for k, v in bound.items():
            if not isinstance(k, str):
                raise ValidationFailure(
                    f"Parameter key must be a string, got {type(k).__name__}.",
                    sql=sql,
                    category="bad_param",
                )
            bound_normalised[k.lstrip(":")] = v

        missing = sorted(n for n in names if n not in bound_normalised)
        if missing:
            raise ValidationFailure(
                f"SQL references unbound parameter(s): {missing}.",
                sql=sql,
                category="unbound_param",
            )

        # Every bound value must be a JSON-primitive scalar.
        for k, v in bound_normalised.items():
            if not _is_primitive(v):
                raise ValidationFailure(
                    f"Parameter {k!r} has a non-primitive value "
                    f"({type(v).__name__}). Only str, int, float, "
                    f"bool, or None are allowed.",
                    sql=sql,
                    category="bad_param_value",
                )


# ---------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------


def _default_schema() -> dict[str, frozenset[str]]:
    """Lazy import of the default schema registry."""
    from backend.services.schema_registry import SCHEMA_TABLES

    return dict(SCHEMA_TABLES)


def _first_significant_token(sql: str) -> str:
    """Return the first significant verb in ``sql``.

    Strips a leading ``WITH`` so ``WITH x AS (...) SELECT ...`` is
    correctly identified as a read query. Returns the empty string
    when no token is found.
    """
    cleaned = re.sub(r"^\s*WITH\b", "", sql, count=1, flags=re.IGNORECASE).lstrip()
    # After stripping WITH, the first token is the CTE name (e.g.
    # "x AS"). The actual verb is the first occurrence of SELECT,
    # INSERT, UPDATE, DELETE, etc. We scan for the first SQL verb
    # by looking for word boundaries.
    for match in _RE_WORD.finditer(cleaned):
        token = match.group(1).upper()
        if token in (
            "SELECT",
            "WITH",
            "INSERT",
            "UPDATE",
            "DELETE",
            "DROP",
            "TRUNCATE",
            "ALTER",
            "CREATE",
            "GRANT",
            "REVOKE",
            "MERGE",
            "CALL",
            "COPY",
            "EXEC",
            "EXPLAIN",
            "SHOW",
        ):
            return token
    return ""


def _is_primitive(value: Any) -> bool:
    """Return ``True`` if ``value`` is a JSON-primitive scalar.

    ``datetime`` / ``date`` / ``Decimal`` / ``UUID`` are *not*
    primitive at the JSON layer. The executor normalises those
    types before the validator runs, so they should not appear
    here in practice. We reject them to be safe.
    """
    return value is None or isinstance(value, (str, int, float, bool))


def _split_select_where_order(sql: str) -> tuple[str, str, str]:
    """Return the ``SELECT`` projection, the ``WHERE`` body, and the
    ``ORDER BY`` body.

    The split is intentionally coarse: we look for the *first*
    ``FROM`` to end the projection, the *first* ``WHERE`` to start
    the where body, and the *first* ``ORDER BY`` to start the
    order body. Anything after ``ORDER BY`` is the order body
    until end-of-string (or ``LIMIT``, which we ignore for the
    purpose of column validation).
    """
    upper = sql.upper()
    from_idx = upper.find(" FROM ")
    if from_idx == -1:
        projection = sql
    else:
        projection = sql[:from_idx]

    where_body = ""
    where_idx = upper.find(" WHERE ", from_idx if from_idx != -1 else 0)
    if where_idx != -1:
        # WHERE body is until the next GROUP BY / ORDER BY / LIMIT /
        # HAVING. We are conservative and stop at the first one.
        end_match = re.search(
            r"\b(GROUP\s+BY|ORDER\s+BY|LIMIT|HAVING)\b",
            upper[where_idx + 7 :],
            re.IGNORECASE,
        )
        end = where_idx + 7 + (end_match.start() if end_match else len(upper))
        where_body = sql[where_idx:end]

    order_body = ""
    order_match = re.search(r"\bORDER\s+BY\b", upper)
    if order_match:
        order_body = sql[order_match.end():]

    return projection, where_body, order_body


def _extract_order_by(sql: str) -> str:
    """Return the body of the ``ORDER BY`` clause, or empty."""
    _, _, order = _split_select_where_order(sql)
    return order


def _extract_identifiers(text: str) -> Iterable[str]:
    """Yield every identifier in ``text``.

    Identifiers that are immediately preceded by a ``.`` (table
    qualifiers like ``CaseMaster.CaseMasterID``) are returned as
    the column part only — the table part is checked separately.
    """
    if not text:
        return
    for match in _RE_WORD.finditer(text):
        identifier = match.group(1)
        # ``.identifier`` -> "identifier"
        yield identifier


__all__ = [
    "ALLOWED_CLAUSE_TOKENS",
    "DEFAULT_FORBIDDEN_TOKENS",
    "DEFAULT_FORBIDDEN_VERBS",
    "DEFAULT_READ_ONLY_VERBS",
    "SQLValidationService",
]
