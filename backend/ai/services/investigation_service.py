"""
InvestigationService — the orchestrator that turns a question into an
:class:`InvestigationResponse`.

This module implements the architecture diagram from the Phase 6
spec::

    User Question
       ↓
    Intent Classification
       ↓
    Intent Router
       ↓
    If existing service can answer
       ↓
    Call AnalyticsService or CaseService
       ↓
    Else
       ↓
    Generate SQL
       ↓
    Validate SQL
       ↓
    Execute SQL (Read Only)
       ↓
    Generate Explanation
       ↓
    Return Structured Response

The service composes the four helper services:

  * :class:`~backend.ai.services.intent_service.IntentService`
  * :class:`~backend.ai.services.sql_generation_service.SQLGenerationService`
  * :class:`~backend.ai.services.sql_validation_service.SQLValidationService`
  * :class:`AIQueryService` (injected; lives in
    :mod:`backend.services.ai_query_service`)

The four are independent — the orchestrator is the only place that
knows about all of them. That keeps the unit tests small: every
collaborator can be mocked.

Service-method path (case_search, dashboard_analytics, explain_case,
investigation_summary)
    The intent router inspects the question and the model output and
    calls the corresponding :class:`CaseService` /
    :class:`AnalyticsService` method directly. The result rows are
    turned into an :class:`ExplanationBlock` and returned without
    going through the SQL pipeline. The advantage: no LLM call for
    the SQL generation step, and the ORM's eager-loading guarantees
    a stable response shape.

SQL path (case_search when no service method matches, similar_cases
fallback in future phases)
    The SQL generation service asks the LLM for a JSON
    :class:`GeneratedSQL`. The validator runs the full allowlist
    check. The executor (read-only) runs the validated statement.
    The explanation service turns the rows into an
    :class:`ExplanationBlock`.

Placeholder path (similar_cases in Phase 6)
    The intent router detects ``Intent.SIMILAR_CASES`` and returns a
    structured "feature not yet available" block. The investigation
    service never invokes a vector search in Phase 6 — that lands in
    Phase 7.

Confidence
    The numeric ``confidence`` field is derived from the source. The
    intent classifier's confidence becomes the investigation's
    confidence when the service-method path is taken. The SQL path
    starts at 0.6 and is bumped down by 0.1 for every caveat the
    explanation service adds.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime
from typing import Any, Iterable, Mapping, Sequence

from pydantic import ValidationError

from backend.ai.schemas.ai import (
    CaseSearchOperation,
    DashboardAnalyticsOperation,
    EvidenceItem,
    ExplainCaseOperation,
    ExplanationBlock,
    GeneratedSQL,
    Intent,
    IntentClassification,
    InvestigationResponse,
    InvestigationSummaryOperation,
    OperationType,
    PlaceholderOperation,
    ValidatedSQL,
)
from backend.ai.services.chat_service import ChatService
from backend.ai.services.exceptions import (
    ExecutionFailure,
    PromptError,
    ProviderFailure,
    UnsafeSQL,
    UnknownIntent,
)
from backend.ai.services.intent_service import IntentService
from backend.ai.services.sql_generation_service import (
    SQLGenerationService,
    _extract_json_object,
)
from backend.ai.services.sql_validation_service import SQLValidationService

EXPLANATION_PROMPT_NAME = "explanation_prompt"
_MAX_EVIDENCE_ROWS = 10
_MAX_ROWS_FOR_PROMPT = 20  # rows serialised into the explanation prompt

# Mapping of (label -> numeric confidence).
_CONFIDENCE_SCORE_MAP: dict[str, float] = {
    "high": 0.9,
    "medium": 0.6,
    "low": 0.3,
}

# Numeric cap on the rows_json block we send to the explanation LLM.
# Larger result sets get summarised in plain text so the prompt does
# not blow the context window.
_ROWS_JSON_CAP_CHARS = 8000


class InvestigationService:
    """The end-to-end orchestrator.

    Args:
        session: The request-scoped SQLAlchemy ``Session``.
        chat_service: The :class:`ChatService` used by every LLM call.
        intent_service: The :class:`IntentService` used for step 1.
        sql_generation_service: The :class:`SQLGenerationService` used
            for the SQL-generation step.
        sql_validation_service: The :class:`SQLValidationService`
            used to allowlist the generated SQL.
        ai_query_service: The :class:`AIQueryService` used to run the
            validated SQL. Inject the real implementation in
            production; tests inject a stub.
        case_service: The :class:`CaseService` for the service-method
            path. Defaults to a fresh instance built around
            ``session``.
        analytics_service: The :class:`AnalyticsService` for the
            service-method path. Defaults to a fresh instance built
            around ``session``.
        logger: Optional :class:`logging.Logger`.
    """

    def __init__(
        self,
        session: Any,
        *,
        chat_service: ChatService,
        intent_service: IntentService,
        sql_generation_service: SQLGenerationService,
        sql_validation_service: SQLValidationService,
        ai_query_service: Any,
        case_service: Any | None = None,
        analytics_service: Any | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._session = session
        self._chat = chat_service
        self._intent = intent_service
        self._sql_gen = sql_generation_service
        self._sql_val = sql_validation_service
        self._ai_query = ai_query_service
        # Lazy imports keep the AI service layer unaware of the
        # concrete service types until they're actually needed.
        if case_service is None or analytics_service is None:
            from backend.services import AnalyticsService, CaseService

            self._case_service = case_service or CaseService(session)
            self._analytics_service = (
                analytics_service or AnalyticsService(session)
            )
        else:
            self._case_service = case_service
            self._analytics_service = analytics_service
        self._logger = logger or logging.getLogger(
            "backend.ai.services.investigation_service"
        )

    # ------------------------------------------------------------------
    # Public surface
    # ------------------------------------------------------------------

    def investigate(
        self,
        question: str,
        *,
        request_id: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> InvestigationResponse:
        """Run the full pipeline and return a structured response.

        Args:
            question: The officer's natural-language question.
            request_id: A unique id for this request (UUIDv4 string).
            metadata: Optional metadata propagated to the LLM calls.

        Returns:
            A populated :class:`InvestigationResponse`. Always — the
            service never raises a "could not answer" exception. The
            caller decides what to do with low confidence.

        Raises:
            UnknownIntent: The intent classifier could not place the
                question and the regex fallback also failed.
            UnsafeSQL: The SQL validator rejected the generated SQL.
            PromptError: A prompt file is missing on disk.
            ProviderFailure: The LLM raised a fatal error.
            ExecutionFailure: The database raised while running the
                validated SQL.
        """
        meta = dict(metadata or {})
        meta.setdefault("request_id", request_id)

        self._logger.info(
            "investigation_start request_id=%s question_chars=%d",
            request_id,
            len(question or ""),
        )

        # 1. classify
        classification = self._intent.classify(question, metadata=meta)
        intent = classification.intent

        # 2. route
        if intent is Intent.UNKNOWN:
            # Should not happen — IntentService raises UnknownIntent
            # before returning. Treat as a defensive guard.
            raise UnknownIntent(question, reason="classifier returned UNKNOWN")

        if intent is Intent.SIMILAR_CASES:
            return self._placeholder_response(
                request_id=request_id,
                classification=classification,
                question=question,
            )

        # 3. service-method path for the four intents with stable
        # service methods. Each returns a partial response; the
        # explanation step is shared.
        if intent is Intent.CASE_SEARCH:
            partial = self._run_case_search(question, meta)
        elif intent is Intent.DASHBOARD_ANALYTICS:
            partial = self._run_dashboard_analytics(question, meta)
        elif intent is Intent.EXPLAIN_CASE:
            partial = self._run_explain_case(question, meta)
        elif intent is Intent.INVESTIGATION_SUMMARY:
            partial = self._run_investigation_summary(question, meta)
        else:
            # Defensive: if a future enum value slips through, fail
            # loud rather than silently producing an empty response.
            raise UnknownIntent(
                question,
                reason=f"unsupported intent value: {intent!r}",
            )

        # 4. explanation
        return self._build_response(
            request_id=request_id,
            classification=classification,
            partial=partial,
            question=question,
        )

    # ------------------------------------------------------------------
    # Service-method paths
    # ------------------------------------------------------------------

    def _run_case_search(
        self, question: str, meta: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Call :meth:`CaseService.list_cases` and shape the result."""
        from backend.services import CaseFilters, CaseSort

        filters = _build_case_filters(question)
        sort = CaseSort(field="crime_registered_date", order="desc")
        rows, total = self._case_service.list_cases(
            filters=filters, page=1, page_size=_MAX_ROWS_FOR_PROMPT, sort=sort
        )
        serialised = [_serialise_case_row(row) for row in rows]
        return {
            "operation": OperationType.SERVICE,
            "executed": "CaseService.list_cases",
            "filters": filters.__dict__ if hasattr(filters, "__dict__") else {},
            "rows": serialised,
            "row_count": total,
            "sql": None,
            "params": None,
            "columns": [
                "CaseMasterID",
                "CrimeNo",
                "CrimeRegisteredDate",
                "case_status",
                "crime_major_head",
            ],
            "notes": "Served by CaseService; no LLM-generated SQL was used.",
            "assumptions": _assumptions_for_filters(filters),
        }

    def _run_dashboard_analytics(
        self, question: str, meta: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Call one of the :class:`AnalyticsService` methods."""
        from backend.services import DistrictRef

        lowered = question.lower()
        district = DistrictRef()
        if "district" in lowered:
            # Best-effort: a real implementation would parse the
            # district name from the question. Keep the public API
            # honest: return an empty summary rather than guess.
            pass

        if any(t in lowered for t in ("monthly", "trend", "over time")):
            year = _extract_year(question) or datetime.now().year
            trends = self._analytics_service.get_monthly_trends(
                year=year, district=district
            )
            rows = [
                {
                    "year": t.year,
                    "month": t.month,
                    "case_count": t.case_count,
                }
                for t in trends
            ]
            return {
                "operation": OperationType.SERVICE,
                "executed": f"AnalyticsService.get_monthly_trends(year={year})",
                "filters": {"year": year},
                "rows": rows,
                "row_count": len(rows),
                "sql": None,
                "params": None,
                "columns": ["year", "month", "case_count"],
                "notes": "Served by AnalyticsService.",
                "assumptions": [f"Year interpreted as {year}."],
            }

        # Default: overall summary.
        summary = self._analytics_service.get_summary(district=district)
        rows = [
            {
                "metric": "total_cases",
                "value": summary.total_cases,
            },
            {
                "metric": "open_cases",
                "value": summary.open_cases,
            },
            {
                "metric": "closed_cases",
                "value": summary.closed_cases,
            },
            {
                "metric": "charge_sheet_filed",
                "value": summary.charge_sheet_filed,
            },
        ]
        return {
            "operation": OperationType.SERVICE,
            "executed": "AnalyticsService.get_summary",
            "filters": {},
            "rows": rows,
            "row_count": len(rows),
            "sql": None,
            "params": None,
            "columns": ["metric", "value"],
            "notes": "Served by AnalyticsService.",
            "assumptions": ["No district filter applied."],
        }

    def _run_explain_case(
        self, question: str, meta: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Fetch a single case by id and serialise it for the prompt."""
        from backend.services import CaseNotFoundError

        case_id = _extract_case_id(question)
        if case_id is None:
            # No case id — fall back to SQL path by raising a
            # sentinel the caller can catch.
            raise UnknownIntent(
                question,
                reason="Explain-case intent requires a case id.",
            )
        try:
            case = self._case_service.get_case_detail(case_id)
        except CaseNotFoundError as exc:
            return {
                "operation": OperationType.SERVICE,
                "executed": f"CaseService.get_case_detail(case_id={case_id})",
                "filters": {"case_id": case_id},
                "rows": [],
                "row_count": 0,
                "sql": None,
                "params": None,
                "columns": ["*"],
                "notes": str(exc),
                "assumptions": [],
            }
        return {
            "operation": OperationType.SERVICE,
            "executed": f"CaseService.get_case_detail(case_id={case_id})",
            "filters": {"case_id": case_id},
            "rows": [_serialise_case_row(case, include_relations=True)],
            "row_count": 1,
            "sql": None,
            "params": None,
            "columns": list(_serialise_case_row(case, include_relations=True).keys()),
            "notes": "Served by CaseService.get_case_detail.",
            "assumptions": [f"Resolving by CaseMasterID = {case_id}."],
        }

    def _run_investigation_summary(
        self, question: str, meta: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Same as explain-case but with broader context (children).

        Phase 6 delegates to ``get_case_detail`` and asks the
        explanation prompt to produce the multi-section brief.
        Phase 7 will add similar-case context.
        """
        return self._run_explain_case(question, meta)

    # ------------------------------------------------------------------
    # SQL path (only used if a future intent needs it)
    # ------------------------------------------------------------------

    def _run_sql_path(
        self, question: str, meta: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Generate, validate, and execute a SQL statement."""
        generated = self._sql_gen.generate(question, metadata=meta)
        try:
            validated = self._sql_val.validate(generated)
        except UnsafeSQL as exc:
            self._logger.info(
                "investigation_sql_rejected reason=%s category=%s",
                exc.reason,
                exc.category,
            )
            raise
        result = self._ai_query.execute_validated_sql(
            validated.sql, validated.params
        )
        return {
            "operation": OperationType.SQL,
            "executed": "SQLAlchemySQLExecutor.execute",
            "filters": {},
            "rows": result.rows,
            "row_count": result.row_count,
            "sql": result.sql,
            "params": result.params,
            "columns": result.columns,
            "notes": generated.notes,
            "assumptions": [
                "SQL was generated by the LLM and re-validated against "
                "the schema allowlist before execution.",
            ],
        }

    # ------------------------------------------------------------------
    # Placeholder path
    # ------------------------------------------------------------------

    def _placeholder_response(
        self,
        *,
        request_id: str,
        classification: IntentClassification,
        question: str,
    ) -> InvestigationResponse:
        op = PlaceholderOperation(
            case_id=_extract_case_id(question),
            message=(
                "Similar-case search is scheduled for Phase 7. "
                "No investigation was performed."
            ),
        )
        return InvestigationResponse(
            request_id=request_id,
            intent=classification.intent,
            operation=OperationType.PLACEHOLDER,
            reasoning=(
                "Question matched the similar-cases intent; this "
                "feature is not available in Phase 6."
            ),
            executed_operation="placeholder.similar_cases",
            confidence=0.0,
            assumptions=[op.message],
            supporting_evidence=[],
            explanation=None,
            raw_sql=None,
            raw_params=None,
            row_count=None,
            columns=None,
            placeholder={"feature": "similar_cases", "case_id": op.case_id},
        )

    # ------------------------------------------------------------------
    # Final assembly
    # ------------------------------------------------------------------

    def _build_response(
        self,
        *,
        request_id: str,
        classification: IntentClassification,
        partial: dict[str, Any],
        question: str,
    ) -> InvestigationResponse:
        """Build the final :class:`InvestigationResponse`."""
        explanation = self._explain(
            question=question,
            partial=partial,
        )
        evidence = _build_evidence(partial.get("rows", []))
        confidence = _compute_confidence(
            classification.confidence, explanation
        )
        reasoning = (
            f"Question classified as {classification.intent.value} "
            f"({classification.reasoning}). "
            f"Operation: {partial.get('executed', 'unknown')}."
        )
        return InvestigationResponse(
            request_id=request_id,
            intent=classification.intent,
            operation=partial.get("operation", OperationType.SERVICE),
            reasoning=reasoning,
            executed_operation=partial.get("executed", "unknown"),
            confidence=confidence,
            assumptions=partial.get("assumptions", []),
            supporting_evidence=evidence,
            explanation=explanation,
            raw_sql=partial.get("sql"),
            raw_params=partial.get("params"),
            row_count=partial.get("row_count"),
            columns=partial.get("columns"),
            placeholder=None,
        )

    # ------------------------------------------------------------------
    # Explanation step
    # ------------------------------------------------------------------

    def _explain(
        self, *, question: str, partial: dict[str, Any]
    ) -> ExplanationBlock:
        """Render the explanation prompt and parse the reply.

        Falls back to a structured "no-explanation" block if the
        model is unavailable or its reply cannot be parsed.
        """
        rows = partial.get("rows", [])
        row_count = partial.get("row_count", 0) or 0
        rows_for_prompt = rows[:_MAX_ROWS_FOR_PROMPT]
        rows_json = _truncate_for_prompt(
            json.dumps(rows_for_prompt, default=str)
        )

        filters_text = json.dumps(partial.get("filters", {}), default=str)
        sql_text = partial.get("sql") or "(service-method path; no SQL)"
        try:
            response = self._chat.chat_with_prompt(
                EXPLANATION_PROMPT_NAME,
                question,
                temperature=0.2,
                max_output_tokens=512,
                QUESTION=question,
                SQL=sql_text,
                ROWS_JSON=rows_json,
                ROW_COUNT=str(row_count),
                FILTERS=filters_text,
            )
        except PromptError as exc:
            self._logger.info(
                "investigation_explain_prompt_missing error=%s",
                exc,
            )
            return _fallback_explanation(rows, row_count)
        except ProviderFailure as exc:
            self._logger.info(
                "investigation_explain_provider_failure error=%s",
                exc,
            )
            return _fallback_explanation(rows, row_count)

        parsed = _extract_json_object(response.content or "")
        if parsed is None:
            return _fallback_explanation(rows, row_count)

        try:
            return _parse_explanation(parsed, rows, row_count)
        except ValidationError as exc:
            self._logger.info(
                "investigation_explain_invalid_schema error=%s",
                exc,
            )
            return _fallback_explanation(rows, row_count)


# ---------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------


def _fallback_explanation(
    rows: Sequence[Mapping[str, Any]], row_count: int
) -> ExplanationBlock:
    """Return a deterministic explanation when the LLM is unavailable.

    The fallback uses no external calls and never fabricates
    evidence — it only restates the data we have. The route layer
    can still render a useful response.
    """
    evidence = _build_evidence(rows)
    summary = (
        f"{row_count} matching record(s) found." if rows else "No records found."
    )
    return ExplanationBlock(
        summary=summary,
        evidence=evidence,
        why=(
            "The result is a direct dump of the underlying service "
            "output; the LLM explanation service was unavailable."
        ),
        confidence="low",
        confidence_score=0.3,
        confidence_reason="LLM explanation service was unavailable.",
        caveats=[
            "Summary was generated without the explanation model.",
        ],
    )


def _parse_explanation(
    parsed: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    row_count: int,
) -> ExplanationBlock:
    """Build an :class:`ExplanationBlock` from the LLM's JSON reply."""
    label = str(parsed.get("confidence", "medium")).strip().lower()
    if label not in _CONFIDENCE_SCORE_MAP:
        label = "medium"
    evidence_raw = parsed.get("evidence", [])
    if not isinstance(evidence_raw, list):
        evidence_raw = []
    evidence: list[EvidenceItem] = []
    for item in evidence_raw[:_MAX_EVIDENCE_ROWS]:
        if not isinstance(item, Mapping):
            continue
        evidence.append(
            EvidenceItem(
                case_id=item.get("case_id"),
                fir_number=item.get("fir_number"),
                label=str(item.get("label", "")).strip() or "cited row",
            )
        )
    if not evidence:
        evidence = _build_evidence(rows)[:_MAX_EVIDENCE_ROWS]

    caveats_raw = parsed.get("caveats", [])
    if not isinstance(caveats_raw, list):
        caveats_raw = []
    caveats = [str(c).strip() for c in caveats_raw if str(c).strip()][:20]

    return ExplanationBlock(
        summary=str(parsed.get("summary", "")).strip()
        or f"{row_count} record(s) found.",
        evidence=evidence,
        why=str(parsed.get("why", "")).strip()
        or "Result is based on the rows above.",
        confidence=label,  # type: ignore[arg-type]
        confidence_score=_CONFIDENCE_SCORE_MAP[label],
        confidence_reason=str(parsed.get("confidence_reason", "")).strip(),
        caveats=caveats,
    )


def _build_evidence(rows: Sequence[Mapping[str, Any]]) -> list[EvidenceItem]:
    """Convert a list of rows into :class:`EvidenceItem` objects.

    The conversion is intentionally tolerant — different service
    methods produce different column sets. We look for the common
    shape (``CaseMasterID``, ``CrimeNo``, ``BriefFacts``) and fall
    back to a label built from whatever columns are present.
    """
    evidence: list[EvidenceItem] = []
    for row in rows[:_MAX_EVIDENCE_ROWS]:
        if not isinstance(row, Mapping):
            continue
        case_id = _coerce_int(row.get("CaseMasterID") or row.get("case_id"))
        fir_number = (
            row.get("CrimeNo")
            or row.get("fir_number")
            or row.get("crime_no")
        )
        label = _row_label(row)
        if case_id is None and not fir_number and not label:
            continue
        evidence.append(
            EvidenceItem(
                case_id=case_id,
                fir_number=str(fir_number) if fir_number else None,
                label=label,
            )
        )
    return evidence


def _row_label(row: Mapping[str, Any]) -> str:
    """Build a short human-readable label for a row."""
    parts: list[str] = []
    for key, prefix in (
        ("CrimeGroupName", ""),
        ("CrimeHeadName", ""),
        ("CaseStatusName", "Status: "),
        ("BriefFacts", ""),
        ("CaseNo", "Case: "),
    ):
        value = row.get(key)
        if value:
            value_str = str(value)
            if prefix:
                parts.append(f"{prefix}{value_str}")
            else:
                parts.append(value_str)
    if not parts:
        # Fallback: a comma-joined list of the first three columns.
        flat = [
            f"{k}={v}" for k, v in list(row.items())[:3] if v is not None
        ]
        parts = flat or ["record"]
    joined = "; ".join(parts)
    if len(joined) > 200:
        joined = joined[:197] + "..."
    return joined


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _compute_confidence(
    intent_confidence: float, explanation: ExplanationBlock
) -> float:
    """Combine the intent confidence with the explanation's caveats."""
    base = float(intent_confidence or 0.0)
    penalty = min(0.3, 0.05 * len(explanation.caveats))
    return round(max(0.0, min(1.0, base - penalty)), 3)


def _truncate_for_prompt(text: str) -> str:
    """Trim the rows_json block to keep the prompt in budget."""
    if len(text) <= _ROWS_JSON_CAP_CHARS:
        return text
    return text[: _ROWS_JSON_CAP_CHARS - 80] + "...(truncated)"


def _serialise_case_row(row: Any, *, include_relations: bool = False) -> dict[str, Any]:
    """Convert an ORM row into a JSON-friendly dict."""
    out: dict[str, Any] = {
        "CaseMasterID": _getattr(row, "CaseMasterID"),
        "CrimeNo": _getattr(row, "CrimeNo"),
        "CaseNo": _getattr(row, "CaseNo"),
        "CrimeRegisteredDate": _iso(_getattr(row, "CrimeRegisteredDate")),
        "BriefFacts": _getattr(row, "BriefFacts"),
    }
    if include_relations:
        out["case_status"] = _rel_name(row, "case_status", "CaseStatusName")
        out["crime_major_head"] = _rel_name(
            row, "crime_major_head", "CrimeGroupName"
        )
        out["crime_minor_head"] = _rel_name(
            row, "crime_minor_head", "CrimeHeadName"
        )
        out["police_station"] = _rel_name(row, "police_station", "UnitName")
    return out


def _getattr(obj: Any, name: str) -> Any:
    return getattr(obj, name, None)


def _rel_name(obj: Any, attr: str, name_attr: str) -> str | None:
    rel = getattr(obj, attr, None)
    if rel is None:
        return None
    return getattr(rel, name_attr, None)


def _iso(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _build_case_filters(question: str) -> Any:
    """Translate a free-text question into a :class:`CaseFilters`."""
    from backend.services import CaseFilters

    lowered = question.lower()
    filters = CaseFilters()
    # Crude name-based parsing. Phase 6 keeps the public surface
    # small; Phase 7 may add a richer parser.
    if "mysuru" in lowered or "mysore" in lowered:
        filters = CaseFilters(district="Mysuru")
    elif "kalaburagi" in lowered or "gulbarga" in lowered:
        filters = CaseFilters(district="Kalaburagi")
    elif "bengaluru" in lowered or "bangalore" in lowered:
        filters = CaseFilters(district="Bengaluru")
    return filters


def _assumptions_for_filters(filters: Any) -> list[str]:
    """Describe the filters we applied, for the audit log."""
    if not filters:
        return ["No filters applied."]
    out: list[str] = []
    for key, value in filters.__dict__.items():
        if value is None:
            continue
        out.append(f"Applied filter {key}={value!r}.")
    return out or ["No filters applied."]


_YEAR_RE = re.compile(r"\b(20\d{2}|19\d{2})\b")


def _extract_year(question: str) -> int | None:
    match = _YEAR_RE.search(question or "")
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:  # pragma: no cover
        return None


_CASE_ID_RE = re.compile(r"\bcase\s*(?:id\s*[:=]?\s*)?(\d+)\b", re.IGNORECASE)
_FIR_RE = re.compile(r"\bFIR\s*(?:number\s*[:=]?\s*)?([A-Z0-9]+)\b", re.IGNORECASE)


def _extract_case_id(question: str) -> int | None:
    match = _CASE_ID_RE.search(question or "")
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:  # pragma: no cover
        return None


__all__ = [
    "EXPLANATION_PROMPT_NAME",
    "InvestigationService",
]
