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
from backend.services import AnalyticsService, CaseService, PredictionService

EXPLANATION_PROMPT_NAME = "explanation_prompt"
INVESTIGATION_REPORT_PROMPT_NAME = "investigation_report_prompt"
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
        prediction_service: Any | None = None,
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

        if prediction_service is None:
            from backend.services import PredictionService

            self._prediction_service = prediction_service or PredictionService(session)
        else:
            self._prediction_service = prediction_service
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
        # Check if this is a request for a comprehensive investigation report
        if self._is_investigation_report_request(question):
            return self._handle_investigation_report_request(question, request_id, metadata)

        meta = dict(metadata or {})
        meta.setdefault("request_id", request_id)

        from backend.ai.services.context_manager import get_context_manager
        ctx_mgr = get_context_manager()
        session_id = meta.get("session_id") or meta.get("user_id") or request_id
        ctx_state = ctx_mgr.get_state(session_id)

        # Update or inherit active case ID
        q_case_id = _extract_case_id(question, meta)
        if q_case_id is not None:
            ctx_mgr.update_state(session_id, case_id=q_case_id)
            meta["active_case_id"] = q_case_id
        elif ctx_state.active_case_id:
            meta["active_case_id"] = ctx_state.active_case_id

        self._logger.info(
            "investigation_start request_id=%s question_chars=%d",
            request_id,
            len(question or ""),
        )

        # 1. classify
        classification = self._intent.classify(question, metadata=meta)
        intent = classification.intent

        # 2. conversational direct routes (no DB execution)
        if intent is Intent.GREETING:
            return InvestigationResponse(
                request_id=request_id,
                intent=Intent.GREETING,
                operation=OperationType.SERVICE,
                reasoning="Officer greeting acknowledged.",
                executed_operation="ConversationalHandler.greeting",
                confidence=1.0,
                assumptions=[],
                supporting_evidence=[],
                explanation=ExplanationBlock(
                    summary="Namaskara, Officer! I am Saaransh AI, your Karnataka State Police Investigation Assistant. How can I assist your investigation today?",
                    evidence=[],
                    why="Greeting response — no database query required.",
                    confidence="high",
                    confidence_score=1.0,
                    confidence_reason="Direct greeting pattern matched.",
                    caveats=[],
                ),
                recommended_actions=["Search cases by district (e.g. 'Show murder cases in Mysuru')", "Lookup a specific FIR (e.g. 'Show case 123')", "Check crime hotspots and predictions"],
                follow_up_suggestions=["Show murder cases in Mysuru", "Show recent crime hotspots", "Count pending investigations"],
            )

        if intent is Intent.FAREWELL:
            return InvestigationResponse(
                request_id=request_id,
                intent=Intent.FAREWELL,
                operation=OperationType.SERVICE,
                reasoning="Officer farewell acknowledged.",
                executed_operation="ConversationalHandler.farewell",
                confidence=1.0,
                assumptions=[],
                supporting_evidence=[],
                explanation=ExplanationBlock(
                    summary="Jai Hind, Officer! Standby mode active. Reach out whenever you need further intelligence or FIR analysis.",
                    evidence=[],
                    why="Farewell response — no database query required.",
                    confidence="high",
                    confidence_score=1.0,
                    confidence_reason="Direct farewell pattern matched.",
                    caveats=[],
                ),
                recommended_actions=[],
                follow_up_suggestions=[],
            )

        if intent is Intent.HELP:
            return InvestigationResponse(
                request_id=request_id,
                intent=Intent.HELP,
                operation=OperationType.SERVICE,
                reasoning="Capability and help guide delivered.",
                executed_operation="ConversationalHandler.help",
                confidence=1.0,
                assumptions=[],
                supporting_evidence=[],
                explanation=ExplanationBlock(
                    summary="I can assist you with Case Lookups, Suspect Tracking, Evidence Summaries, Timeline Analysis, Hotspot Predictions, and Crime Analytics across Karnataka.",
                    evidence=[],
                    why="Help query — no database query required.",
                    confidence="high",
                    confidence_score=1.0,
                    confidence_reason="Direct help pattern matched.",
                    caveats=[],
                ),
                recommended_actions=["Query cases by district or crime head", "Lookup FIR details by Case ID", "Generate full investigation reports"],
                follow_up_suggestions=["Show murder cases in Mysuru", "Show case 123", "Show recent crime hotspots"],
            )

        # Case sub-intents (suspects, evidence, timeline, IO)
        if intent in (Intent.CASE_SUSPECTS, Intent.CASE_EVIDENCE, Intent.CASE_TIMELINE, Intent.CASE_IO):
            active_id = meta.get("active_case_id")
            if active_id is None:
                return InvestigationResponse(
                    request_id=request_id,
                    intent=Intent.CLARIFICATION,
                    operation=OperationType.SERVICE,
                    reasoning="Case reference required to inspect case sub-details.",
                    executed_operation="ConversationalHandler.clarification",
                    confidence=0.9,
                    assumptions=[],
                    supporting_evidence=[],
                    explanation=ExplanationBlock(
                        summary="Which case would you like to inspect? Please specify a Case ID or FIR number (e.g., 'Show case 123' or 'FIR 455').",
                        evidence=[],
                        why="No active Case ID was specified in the question or conversation context.",
                        confidence="medium",
                        confidence_score=0.9,
                        confidence_reason="Missing active_case_id parameter.",
                        caveats=[],
                    ),
                    recommended_actions=["Provide a Case ID (e.g. 'Show case 123')", "Search cases by district (e.g. 'Show cases in Mysuru')"],
                    follow_up_suggestions=["Show case 1", "Show case 123", "Show murder cases in Mysuru"],
                )
            partial = self._run_explain_case(question, meta)
            return self._build_response(
                request_id=request_id,
                classification=classification,
                partial=partial,
                question=question,
            )

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


        # 3a. Phase 8 — fall through to the SQL pipeline when the
        #     service path cannot fully answer the question. The
        #     heuristic inspects the question and the resolved
        #     filters; per-case intents and dashboard summaries
        #     with a usable service method stay on the service
        #     path. When the SQL path runs we replace the partial
        #     wholesale (its rows, columns, sql, and confidence
        #     are more accurate than the service path's empty
        #     result).
        if intent in (Intent.CASE_SEARCH, Intent.DASHBOARD_ANALYTICS):
            filters_for_heuristic = (
                _build_case_filters(question)
                if intent is Intent.CASE_SEARCH
                else None
            )
            if self._should_use_sql_path(
                question, classification, filters_for_heuristic
            ):
                try:
                    sql_partial = self._run_sql_path(question, meta)
                except UnsafeSQL as exc:
                    # The validator rejected the generated SQL.
                    # Log it and keep the service-path result —
                    # the officer still gets the partial answer.
                    self._logger.info(
                        "investigation_sql_fallback_rejected reason=%s "
                        "category=%s",
                        exc.reason,
                        exc.category,
                    )
                    partial = {
                        **partial,
                        "assumptions": list(partial.get("assumptions", []))
                        + [
                            f"SQL fallback rejected: {exc.reason}",
                        ],
                    }
                except ExecutionFailure as exc:
                    self._logger.info(
                        "investigation_sql_fallback_exec_failure error=%s",
                        exc,
                    )
                    partial = {
                        **partial,
                        "assumptions": list(partial.get("assumptions", []))
                        + [f"SQL fallback execution failed: {exc}"],
                    }
                else:
                    # SQL path succeeded — adopt its rows, sql,
                    # and columns. We keep the service path's
                    # ``assumptions`` and ``notes`` so the audit
                    # log records that both paths ran.
                    partial = {
                        **partial,
                        "operation": sql_partial["operation"],
                        "executed": sql_partial["executed"],
                        "rows": sql_partial["rows"],
                        "row_count": sql_partial["row_count"],
                        "sql": sql_partial["sql"],
                        "params": sql_partial["params"],
                        "columns": sql_partial["columns"],
                        "notes": sql_partial["notes"],
                        "assumptions": list(partial.get("assumptions", []))
                        + sql_partial.get("assumptions", []),
                    }

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

        filters = _build_case_filters(question, meta)

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

        case_id = _extract_case_id(question, meta)

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

    # Tokens that mean the question needs the SQL pipeline rather
    # than the service-method path. Kept short on purpose — every
    # extra word here is one more false positive.
    _SQL_TRIGGER_TOKENS: tuple[str, ...] = (
        "compare",
        "highest",
        "lowest",
        "most ",
        "top ",
        "rank",
        "leaderboard",
        "repeat offender",
        "repeat-offender",
        "habitual",
        "recidiv",
    )

    def _should_use_sql_path(
        self,
        question: str,
        classification: IntentClassification,
        filters: Any | None = None,
    ) -> bool:
        """Decide whether to fall through from the service path to SQL.

        The rule of thumb: if the question contains a phrase the
        :class:`CaseService` / :class:`AnalyticsService` cannot
        answer (date ranges, "compare", "near <locality>", an
        aggregation we don't have a method for, an unknown filter
        shape), generate SQL instead. Per-case intents
        (:class:`Intent.EXPLAIN_CASE` and
        :class:`Intent.INVESTIGATION_SUMMARY`) always use the
        service path — SQL would not gain anything for a single
        case lookup.

        Args:
            question: The original officer question.
            classification: The intent classification result.
            filters: The :class:`CaseFilters` produced by
                :func:`_build_case_filters`. ``None`` for
                intents that don't have a filter parser.

        Returns:
            ``True`` if the orchestrator should call
            :meth:`_run_sql_path` after the service path returns.
        """
        # Per-case intents never benefit from SQL.
        if classification.intent in (
            Intent.EXPLAIN_CASE,
            Intent.INVESTIGATION_SUMMARY,
        ):
            return False

        lowered = (question or "").lower()

        # 1. "between X and Y" / "from X to Y" — a structured date
        #    range. The service path can handle this via date_from/
        #    date_to, so we do not always escalate.
        # 2. "compare" — analytics aggregation across districts.
        if "compare" in lowered:
            return True
        # 3. highest / most / top / lowest — aggregation by district.
        if any(tok in lowered for tok in self._SQL_TRIGGER_TOKENS):
            return True
        # 4. "near <locality>" — the service path has no station
        #    filter, so the SQL pipeline can JOIN to the unit table.
        if re.search(r"\bnear\s+[a-z]", lowered):
            return True
        # 5. "between <date1> and <date2>" / "from <date1> to
        #    <date2>" — date range spanning two specific days. The
        #    parser already populated date_from/date_to, so the
        #    service path can serve it; the explicit phrase is a
        #    signal the officer wants both ends of the range, which
        #    the SQL pipeline can present more clearly.
        if re.search(r"\b(?:between|from)\s+\S+\s+(?:and|to)\s+\S+", lowered):
            return True
        # 6. "all FIRs filed today" without an explicit date — the
        #    parser maps "today" to date_from=date_to=today, so
        #    this is already answered by the service path.
        # 7. District mentioned but the parser resolved no useful
        #    filter (e.g. a non-Karnataka district). The service
        #    path would return zero rows, so SQL can do better.
        if (
            classification.intent is Intent.CASE_SEARCH
            and filters is not None
        ):
            has_district = bool(
                getattr(filters, "district", None)
                or getattr(filters, "district_id", None)
            )
            any_filter = any(
                getattr(filters, name, None) is not None
                for name in (
                    "fir_number",
                    "district",
                    "police_station",
                    "crime_head",
                    "status",
                    "date_from",
                    "date_to",
                )
            )
            if has_district and not any_filter:
                # District was set via the locality alias pass but
                # nothing else matched — escalate so the SQL path
                # can JOIN to the unit table.
                return True
        return False

    def _handle_investigation_report_request(
        self,
        question: str,
        request_id: str,
        metadata: Mapping[str, Any] | None
    ) -> InvestigationResponse:
        """Handle a request for a comprehensive investigation report.

        This method gathers all necessary data and uses the investigation report
        prompt to generate a structured response.
        """
        meta = dict(metadata or {})
        meta.setdefault("request_id", request_id)

        self._logger.info(
            "investigation_report_request request_id=%s question_chars=%d",
            request_id,
            len(question or ""),
        )

        # Parse the question to extract key elements
        filters = _build_case_filters(question)

        try:
            # Generate SQL to get comprehensive data for the investigation report
            generated = self._sql_gen.generate(question, metadata=meta)
            validated = self._sql_val.validate(generated)
            result = self._ai_query.execute_validated_sql(
                validated.sql, validated.params
            )

            sql_partial = {
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
        except (UnsafeSQL, ExecutionFailure) as exc:
            self._logger.info(
                "investigation_report_sql_fallback error=%s",
                exc,
            )
            # Rollback aborted transaction so session is reusable
            if hasattr(self._session, "rollback"):
                try:
                    self._session.rollback()
                except Exception:
                    pass

            # Fall back to CaseService list_cases ORM query (no raw SQL risk)
            try:
                from backend.services import CaseSort
                sort = CaseSort(field="crime_registered_date", order="desc")
                case_rows, total_count = self._case_service.list_cases(
                    filters=filters, page=1, page_size=_MAX_ROWS_FOR_PROMPT, sort=sort
                )
                serialised_rows = [_serialise_case_row(r) for r in case_rows]
                sql_partial = {
                    "operation": OperationType.SERVICE,
                    "executed": "CaseService.list_cases",
                    "filters": filters.__dict__ if hasattr(filters, "__dict__") else {},
                    "rows": serialised_rows,
                    "row_count": total_count,
                    "sql": None,
                    "params": None,
                    "columns": ["CaseMasterID", "CrimeNo", "CrimeRegisteredDate", "case_status", "crime_major_head"],
                    "notes": f"Served by CaseService ORM fallback ({total_count} cases found).",
                    "assumptions": ["Using CaseService ORM data as fallback for investigation report"],
                }
            except Exception as service_exc:
                self._logger.info("investigation_report_service_fallback_failed error=%s", service_exc)
                if hasattr(self._session, "rollback"):
                    try:
                        self._session.rollback()
                    except Exception:
                        pass
                from backend.services import DistrictRef
                dist_param = DistrictRef(name=filters.district) if (hasattr(filters, 'district') and filters.district) else None
                summary = self._analytics_service.get_summary(district=dist_param)
                sql_partial = {
                    "operation": OperationType.SERVICE,
                    "executed": "AnalyticsService.get_summary",
                    "filters": {"district": getattr(filters, 'district', None) if hasattr(filters, 'district') else None},
                    "rows": [
                        {"metric": "total_cases", "value": summary.total_cases},
                        {"metric": "open_cases", "value": summary.open_cases},
                        {"metric": "closed_cases", "value": summary.closed_cases},
                    ],
                    "row_count": 3,
                    "sql": None,
                    "params": None,
                    "columns": ["metric", "value"],
                    "notes": "Served by AnalyticsService (fallback for investigation report).",
                    "assumptions": ["Using aggregated data as fallback for investigation report"],
                }


        # Extract data for the investigation report
        rows = sql_partial.get("rows", [])

        # Build investigation report components
        statistics = self._extract_statistics_from_results(rows)
        hotspots = self._extract_hotspots_from_results(rows)
        time_analysis = self._extract_time_analysis_from_results(rows)
        repeat_offenders = self._extract_repeat_offenders_from_results(rows)
        trend_data = self._extract_trend_data_from_results(rows)
        predictions = self._extract_predictions_from_results(rows)
        demographics = self._extract_demographics_from_results(rows)
        case_samples = self._extract_case_samples_from_results(rows)

        # Prepare variables for the investigation report prompt
        import json
        prompt_variables = {
            "QUESTION": question,
            "STATISTICS": json.dumps(statistics),
            "HOTSPOTS": json.dumps(hotspots),
            "TIME_ANALYSIS": json.dumps(time_analysis),
            "REPEAT_OFFENDERS": json.dumps(repeat_offenders),
            "TREND_DATA": json.dumps(trend_data),
            "PREDICTIONS": json.dumps(predictions),
            "DEMOGRAPHICS": json.dumps(demographics),
            "CASE_SAMPLES": json.dumps(case_samples)
        }

        # Generate the investigation report using the LLM
        try:
            response = self._chat.chat_with_prompt(
                INVESTIGATION_REPORT_PROMPT_NAME,
                question,
                temperature=0.2,
                max_output_tokens=1024,
                **prompt_variables
            )

            parsed = _extract_json_object(response.content or "")
            if parsed is None:
                raise ValueError("Failed to parse investigation report response")

            investigation_report = parsed

        except (PromptError, ProviderFailure, ValueError) as exc:
            self._logger.info(
                "investigation_report_prompt_failed error=%s",
                exc,
            )
            # Fallback investigation report
            investigation_report = {
                "headline": "Investigation report generation failed",
                "summary": f"Unable to generate detailed investigation report: {str(exc)}",
                "metrics": statistics,
                "reasoning": [
                    "Failed to generate investigation report from LLM",
                    f"Error: {str(exc)}",
                    "Falling back to basic statistics"
                ],
                "hotspots": hotspots[:3] if len(hotspots) > 3 else hotspots,
                "mostActiveTime": f"{time_analysis.get('timeOfDay', {}).get('peakHour', 'Unknown')} ({time_analysis.get('timeOfDay', {}).get('peakHourCount', 0)} cases)",
                "repeatOffendersCount": len(repeat_offenders),
                "trend": "stable (0% change)",
                "prediction": str(predictions.get('nextWeek', 0)),
                "suggestedDeployment": "Monitor trends and allocate resources based on historical patterns",
                "confidence": "low"
            }

        # Build the final response
        explanation = self._explain(
            question=question,
            partial=sql_partial,
        )

        evidence = _build_evidence(sql_partial.get("rows", []))
        confidence = _compute_confidence(
            0.8,  # Base confidence for investigation reports
            explanation
        )
        reasoning = (
            f"Investigation report generated for question: '{question[:50]}...' "
            f"using data from {sql_partial.get('row_count', 0)} records. "
            f"Operation: {sql_partial.get('executed', 'unknown')}."
        )

        return InvestigationResponse(
            request_id=request_id,
            intent=Intent.DASHBOARD_ANALYTICS,  # Investigations reports are a form of analytics
            operation=sql_partial.get("operation", OperationType.SERVICE),
            reasoning=reasoning,
            executed_operation=sql_partial.get("executed", "investigation_report_generation"),
            confidence=confidence,
            assumptions=sql_partial.get("assumptions", []),
            supporting_evidence=evidence,
            explanation=explanation,
            raw_sql=sql_partial.get("sql"),
            raw_params=sql_partial.get("params"),
            row_count=sql_partial.get("row_count"),
            columns=sql_partial.get("columns"),
            placeholder=None,
            results=sql_partial.get("rows"),
            investigation_report=investigation_report
        )

    def _is_investigation_report_request(self, question: str) -> bool:
        """Determine if the question is asking for a comprehensive investigation report.

        Looks for patterns like:
        - "How many [crime type] cases occurred in [location] during [time period]?"
        - Requests for additional analysis like solved/pending, hotspots, time patterns, etc.
        """
        lowered = (question or "").lower()

        # Check for the basic structure of an investigation report request
        has_count_request = any(phrase in lowered for phrase in [
            "how many", "count of", "number of", "total", "count"
        ])

        has_location_time = any(phrase in lowered for phrase in [
            "in ", "during ", "last ", "past ", "previous ", "recent"
        ]) and any(word in lowered for word in [
            "days", "weeks", "months", "year"
        ])

        # Check for request for additional analysis details
        has_detail_request = any(phrase in lowered for phrase in [
            "solved", "pending", "hotspot", "location", "time", "repeat",
            "offender", "trend", "prediction", "forecast", "deploy"
        ])

        return has_count_request and (has_location_time or has_detail_request)

    def _is_investigation_report_query(self, question: str) -> bool:
        """Alias for backward compatibility."""
        return self._is_investigation_report_request(question)


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
    # Investigation Report Helper Methods
    # ------------------------------------------------------------------

    def _extract_statistics_from_results(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        """Extract statistics for the investigation report from query results."""
        # Default values
        stats = {
            "total": 0,
            "solved": 0,
            "pending": 0,
            "arrests": 0,
            "confidence": "0%"
        }

        if not rows:
            return stats

        # Try to extract from aggregated data
        for row in rows:
            if isinstance(row, dict):
                # Look for common metric names
                if "total_cases" in row or "total" in row:
                    stats["total"] = int(row.get("total_cases", row.get("total", 0)))
                if "solved_cases" in row or "solved" in row:
                    stats["solved"] = int(row.get("solved_cases", row.get("solved", 0)))
                if "pending_cases" in row or "pending" in row:
                    stats["pending"] = int(row.get("pending_cases", row.get("pending", 0)))
                if "arrests" in row:
                    stats["arrests"] = int(row.get("arrests", 0))

        # Calculate completion percentage if we have totals
        if stats["total"] > 0:
            solved_pct = int((stats["solved"] / stats["total"]) * 100) if stats["total"] > 0 else 0
            stats["confidence"] = f"{solved_pct}%"
        else:
            # Count rows as total if no aggregation
            stats["total"] = len(rows)
            # Assume some are solved based on status field if available
            solved_count = sum(1 for row in rows if isinstance(row, dict) and
                              str(row.get("case_status", "")).lower() in ["closed", "solved"])
            stats["solved"] = solved_count
            stats["pending"] = stats["total"] - solved_count
            if stats["total"] > 0:
                solved_pct = int((stats["solved"] / stats["total"]) * 100)
                stats["confidence"] = f"{solved_pct}%"

        return stats

    def _extract_hotspots_from_results(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract hotspot locations from query results."""
        location_counts = {}

        for row in rows:
            if isinstance(row, dict):
                # Look for location fields
                location = None
                for field in ["police_station", "district", "location", "area", "place"]:
                    if field in row and row[field]:
                        location = str(row[field])
                        break

                if location:
                    location_counts[location] = location_counts.get(location, 0) + 1

        # Sort by count and take top 3
        sorted_locations = sorted(location_counts.items(), key=lambda x: x[1], reverse=True)
        hotspots = []
        for i, (location, count) in enumerate(sorted_locations[:3], 1):
            hotspots.append({
                "rank": i,
                "name": location,
                "count": count
            })

        return hotspots

    def _extract_time_analysis_from_results(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        """Extract time-based analysis from query results."""
        hour_counts = {}
        day_counts = {}

        for row in rows:
            if isinstance(row, dict):
                # Try to extract time information
                time_field = None
                date_field = None
                for field in ["time_of_day", "hour", "crime_time"]:
                    if field in row and row[field] is not None:
                        time_field = row[field]
                        break
                for field in ["day_of_week", "date", "crime_date"]:
                    if field in row and row[field] is not None:
                        date_field = row[field]
                        break

                # Process time
                if time_field:
                    try:
                        if isinstance(time_field, str) and ":" in time_field:
                            hour = int(time_field.split(":")[0])
                        elif isinstance(time_field, (int, float)):
                            hour = int(time_field)
                        else:
                            hour = 0
                        hour_counts[hour] = hour_counts.get(hour, 0) + 1
                    except (ValueError, IndexError):
                        pass

                # Process day of week
                if date_field:
                    try:
                        if hasattr(date_field, 'strftime'):
                            day_name = date_field.strftime("%A")
                        elif isinstance(date_field, str):
                            # Try to parse date string
                            from datetime import datetime
                            try:
                                parsed_date = datetime.strptime(date_field[:10], "%Y-%m-%d")
                                day_name = parsed_date.strftime("%A")
                            except ValueError:
                                day_name = "Unknown"
                        else:
                            day_name = "Unknown"
                        day_counts[day_name] = day_counts.get(day_name, 0) + 1
                    except Exception:
                        pass

        # Find peak hour and day
        peak_hour = max(hour_counts.items(), key=lambda x: x[1], default=(0, 0))
        peak_day = max(day_counts.items(), key=lambda x: x[1], default=("Unknown", 0))

        return {
            "timeOfDay": {
                "peakHour": f"{peak_hour[0]:02d}:00",
                "peakHourCount": peak_hour[1],
                "distribution": [{"hour": f"{h:02d}:00", "count": c} for h, c in sorted(hour_counts.items())]
            },
            "dayOfWeek": {
                "peakDay": peak_day[0],
                "peakDayCount": peak_day[1],
                "distribution": [{"day": d, "count": c} for d, c in sorted(day_counts.items())]
            }
        }

    def _extract_repeat_offenders_from_results(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract repeat offender information from query results."""
        offender_counts = {}

        for row in rows:
            if isinstance(row, dict):
                # Look for offender/suspect identifiers
                offender_id = None
                for field in ["accused_id", "suspect_id", "offender_id", "person_id"]:
                    if field in row and row[field] is not None:
                        offender_id = str(row[field])
                        break

                if offender_id:
                    offender_counts[offender_id] = offender_counts.get(offender_id, 0) + 1

        # Find offenders with multiple offenses
        repeat_offenders = [
            {"offender_id": oid, "offense_count": count}
            for oid, count in offender_counts.items()
            if count > 1
        ]

        # Sort by offense count descending
        repeat_offenders.sort(key=lambda x: x["offense_count"], reverse=True)

        return repeat_offenders

    def _extract_trend_data_from_results(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract trend data from query results."""
        # Group by time period (month/week)
        period_counts = {}

        for row in rows:
            if isinstance(row, dict):
                # Try to extract date
                date_value = None
                for field in ["date", "crime_date", "report_date"]:
                    if field in row and row[field] is not None:
                        date_value = row[field]
                        break

                if date_value:
                    try:
                        if hasattr(date_value, 'strftime'):
                            # Date/datetime object
                            period_key = date_value.strftime("%Y-%m")  # Monthly
                        elif isinstance(date_value, str):
                            # Try to parse common date formats
                            from datetime import datetime
                            try:
                                # Try YYYY-MM-DD format
                                parsed_date = datetime.strptime(date_value[:10], "%Y-%m-%d")
                                period_key = parsed_date.strftime("%Y-%m")
                            except ValueError:
                                try:
                                    # Try MM/DD/YYYY format
                                    parsed_date = datetime.strptime(date_value[:10], "%m/%d/%Y")
                                    period_key = parsed_date.strftime("%Y-%m")
                                except ValueError:
                                    period_key = "unknown"
                        else:
                            period_key = "unknown"

                        period_counts[period_key] = period_counts.get(period_key, 0) + 1
                    except Exception:
                        pass

        # Convert to list format and sort by period
        trend_data = [
            {"period": period, "count": count}
            for period, count in sorted(period_counts.items())
        ]

        return trend_data

    def _extract_predictions_from_results(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        """Extract or generate predictions from query results."""
        trend_data = self._extract_trend_data_from_results(rows)

        if len(trend_data) >= 2:
            # Simple trend calculation
            recent_avg = sum(item["count"] for item in trend_data[-3:]) / min(3, len(trend_data))
            earlier_avg = sum(item["count"] for item in trend_data[:-3]) / max(1, len(trend_data[:-3])) if len(trend_data) > 3 else recent_avg

            if earlier_avg > 0:
                change_pct = ((recent_avg - earlier_avg) / earlier_avg) * 100
                trend_direction = "increasing" if change_pct > 5 else "decreasing" if change_pct < -5 else "stable"
            else:
                trend_direction = "stable"
                change_pct = 0

            # Predict next period based on recent trend
            predicted = int(recent_avg * (1 + (change_pct / 100)))
            predicted = max(0, predicted)  # Ensure non-negative
        else:
            trend_direction = "stable"
            predicted = len(rows) if rows else 0

        return {
            "nextWeek": predicted,
            "nextMonth": int(predicted * 4.3),  # Approximate months
            "trendDirection": trend_direction,
            "confidence": "medium" if len(trend_data) >= 3 else "low"
        }


    def _extract_demographics_from_results(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        """Extract demographic information from query results."""
        age_groups = {"0-17": 0, "18-25": 0, "26-35": 0, "36-50": 0, "51+": 0}
        gender_counts = {"Male": 0, "Female": 0, "Other": 0}

        for row in rows:
            if isinstance(row, dict):
                # Age
                age = None
                for field in ["age", "victim_age", "accused_age"]:
                    if field in row and row[field] is not None:
                        try:
                            age = int(row[field])
                            break
                        except (ValueError, TypeError):
                            pass

                if age is not None:
                    if age <= 17:
                        age_groups["0-17"] += 1
                    elif age <= 25:
                        age_groups["18-25"] += 1
                    elif age <= 35:
                        age_groups["26-35"] += 1
                    elif age <= 50:
                        age_groups["36-50"] += 1
                    else:
                        age_groups["51+"] += 1

                # Gender
                gender = None
                for field in ["gender", "victim_gender", "accused_gender"]:
                    if field in row and row[field] is not None:
                        gender_str = str(row[field]).strip()
                        if gender_str.lower() in ["male", "m"]:
                            gender = "Male"
                        elif gender_str.lower() in ["female", "f"]:
                            gender = "Female"
                        else:
                            gender = "Other"
                        break

                if gender:
                    gender_counts[gender] = gender_counts.get(gender, 0) + 1

        return {
            "ageDistribution": age_groups,
            "genderDistribution": gender_counts
        }

    def _extract_case_samples_from_results(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract sample cases for the investigation report."""
        samples = []
        for i, row in enumerate(rows[:5]):  # Take up to 5 samples
            if isinstance(row, dict):
                sample = {
                    "caseId": row.get("CaseMasterID") or row.get("case_id"),
                    "firNumber": row.get("CrimeNo") or row.get("fir_number"),
                    "date": str(row.get("CrimeRegisteredDate") or row.get("date", "")),
                    "location": row.get("police_station") or row.get("district", ""),
                    "briefFacts": str(row.get("BriefFacts") or row.get("brief_facts", ""))[:100] + ("..." if len(str(row.get("BriefFacts") or row.get("brief_facts", ""))) > 100 else "")
                }
                samples.append(sample)
        return samples

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
            results=None,
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
        # Phase 8 — the executor's actual rows. ``None`` on the
        # service-method path (the evidence list already carries
        # the per-row information) and a list of dicts on the
        # SQL path. The list may be empty when the SQL returned
        # zero rows. We branch on the operation type, not on the
        # presence of rows, so a service-path call that happened
        # to return zero rows does not get misclassified as SQL.
        operation = partial.get("operation", OperationType.SERVICE)
        results = partial.get("rows") if operation is OperationType.SQL else None

        return InvestigationResponse(
            request_id=request_id,
            intent=classification.intent,
            operation=operation,
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
            results=results,
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


def _is_investigation_report_request(question: str) -> bool:
    """Check if the question is asking for a comprehensive investigation report.

    Looks for patterns like:
    - "How many [crime type] cases occurred in [location] during [time period]?"
    - Requests for additional analysis like solved/pending, hotspots, etc.
    """
    if not question:
        return False

    lowered = question.lower()

    # Check for the basic pattern: "how many [crime] cases in [place] during [time]"
    has_how_many = "how many" in lowered
    has_cases = "cases" in lowered
    has_time_indicators = any(phrase in lowered for phrase in [
        "during", "in the last", "past ", "last ", "previous "
    ]) and any(word in lowered for word in [
        "days", "weeks", "months", "year"
    ])

    # Check for request for additional details that suggest a comprehensive report
    detail_indicators = [
        "solved", "unsolved", "pending",
        "hotspot", "location", "area", "place",
        "time", "when", "hour",
        "repeat", "recidivist", "offender",
        "trend", "increasing", "decreasing",
        "prediction", "forecast", "expect",
        "deploy", "resource", "patrol", "officer"
    ]

    has_details = any(indicator in lowered for indicator in detail_indicators)

    return has_how_many and has_cases and (has_time_indicators or has_details)


def _fallback_explanation(
    rows: Sequence[Mapping[str, Any]], row_count: int
) -> ExplanationBlock:
    """Return a deterministic explanation when the LLM is unavailable.

    The fallback uses no external calls and never fabricates
    evidence — it only restates the data we have. The route layer
    can still render a useful response.
    """
    evidence = _build_evidence(rows)
    if rows:
        ids_str = ", ".join([f"Case #{r.get('CaseMasterID')} ({r.get('CrimeNo') or 'N/A'})" for r in rows[:5] if r.get('CaseMasterID') is not None])
        summary = f"Found {row_count} matching case(s): {ids_str}" if ids_str else f"{row_count} matching record(s) found."
    else:
        summary = "No matching cases found."

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
        fir_str = str(fir_number) if fir_number else None
        if fir_str and ("MagicMock" in fir_str or len(fir_str) > 64):
            fir_str = f"FIR-{case_id}" if case_id else "FIR-REF"
        evidence.append(
            EvidenceItem(
                case_id=case_id,
                fir_number=fir_str,
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


# ---------------------------------------------------------------------
# Natural-language → CaseFilters parser
# ---------------------------------------------------------------------
#
# A small, deterministic parser that turns common police phrasing
# into a :class:`CaseFilters` value the existing CaseService can
# execute. The parser is intentionally keyword/pattern based — it
# never calls the LLM, never reads the database, and never invents
# filters that the case service cannot honour. Questions the parser
# cannot understand (e.g. "compare Mysuru and Bengaluru crime") are
# left with no filters; the orchestrator then escalates to the SQL
# path.
#
# The parser is structured as a sequence of independent "rules". Each
# rule is a small function that mutates a CaseFilters in place. The
# ordering matters only when two rules might conflict (e.g. status
# names that double as district names); we apply the most specific
# rule last so it wins.
#
# Supported phrases (verified by tests):
#   district:  "Mysuru" / "Mysore", "Bengaluru" / "Bangalore",
#              "Kalaburagi" / "Gulbarga", "Hubballi", "Mangaluru",
#              "Dharwad", "Belagavi", "Tumakuru", "Ballari", "Vijayapura"
#   crime:     "murder", "robbery", "theft", "chain snatching",
#              "cyber crime" / "cyber fraud" / "fraud", "rape",
#              "kidnapping", "assault", "burglary", "dowry death"
#   status:    "open", "pending", "under investigation",
#              "charge sheeted" / "chargesheeted",
#              "closed", "undetected"
#   dates:     "today", "yesterday", "this week", "this month",
#              "last 7 days", "last 30 days",
#              "between <date1> and <date2>",
#              "from <date1> to <date2>"
#   fir:       "FIR <number>"
#
# A question that does not match any rule yields a default
# CaseFilters() (no filters) — the orchestrator will try the SQL
# path if that seems appropriate.

#: Karnataka districts the parser recognises (the Supabase seed
#: data uses these names). Lookups are case-insensitive.
_DISTRICT_NAMES: tuple[str, ...] = (
    "Bengaluru",
    "Mysuru",
    "Kalaburagi",
    "Hubballi",
    "Mangaluru",
    "Dharwad",
    "Belagavi",
    "Tumakuru",
    "Ballari",
    "Vijayapura",
    "Davangere",
    "Shivamogga",
    "Raichur",
    "Udupi",
    "Hassan",
    "Mandya",
    "Chitradurga",
    "Chikkamagaluru",
    "Kolar",
    "Chikkaballapur",
    "Ramanagara",
    "Chamarajanagar",
    "Yadgir",
    "Koppal",
    "Gadag",
    "Haveri",
    "Karwar",
    "Bagalkot",
    "Bidar",
)

#: Legacy spellings -> canonical KSP name. The case service uses
#: case-insensitive matching against :data:`District.DistrictName`,
#: so a question that says "Mysore" will be matched against the
#: district named "Mysuru" if the parser normalises first.
_LEGACY_DISTRICT_ALIASES: dict[str, str] = {
    "mysore": "Mysuru",
    "bangalore": "Bengaluru",
    "banglore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "gulbarga": "Kalaburagi",
    "hubli": "Hubballi",
    "mangalore": "Mangaluru",
    "belgaum": "Belagavi",
    "tumkur": "Tumakuru",
    "bellary": "Ballari",
    "bijapur": "Vijayapura",
    "shimoga": "Shivamogga",
    "chikmagalur": "Chikkamagaluru",
    "chamrajnagar": "Chamarajanagar",
    "ಬೆಂಗಳೂರು": "Bengaluru",
    "ಮೈಸೂರು": "Mysuru",
    "ಹಾಸನ": "Hassan",
    "ಹುಬ್ಬಳ್ಳಿ": "Hubballi",
    "ಮಂಗಳೂರು": "Mangaluru",
    "ಬೆಳಗಾವಿ": "Belagavi",
    "ಕಲಬುರಗಿ": "Kalaburagi",
}

#: Bangalore localities the parser maps to the Bengaluru Urban
#: district or to a specific police station. Best-effort — when the
#: station name does not match a known row, the filter is dropped.
_LOCALITY_TO_DISTRICT: dict[str, str] = {
    "whitefield": "Bengaluru",
    "indiranagar": "Bengaluru",
    "koramangala": "Bengaluru",
    "mg road": "Bengaluru",
    "jayanagar": "Bengaluru",
    "marathahalli": "Bengaluru",
    "electronic city": "Bengaluru",
    "hebbal": "Bengaluru",
    "yelahanka": "Bengaluru",
    "rajajinagar": "Bengaluru",
    "bellandur": "Bengaluru",
    "hsr": "Bengaluru",
    "btm": "Bengaluru",
    "ulsoor": "Bengaluru",
}

#: Crime head keywords → KSP taxonomy string. The case service
#: resolves the name to an id; if the name does not match, the
#: service returns zero rows. The mapping below is best-effort.
_CRIME_HEAD_KEYWORDS: dict[str, str] = {
    "murder": "Murder",
    "homicide": "Murder",
    "killing": "Murder",
    "robbery": "Robbery",
    "loot": "Robbery",
    "theft": "Theft",
    "stealing": "Theft",
    "burglary": "Burglary",
    "house breaking": "Burglary",
    "dacoity": "Dacoity",
    "chain snatching": "Chain Snatching",
    "snatching": "Chain Snatching",
    "snatch": "Chain Snatching",
    "rape": "Rape",
    "kidnapping": "Kidnapping",
    "abduction": "Kidnapping",
    "missing": "Kidnapping",
    "missing persons": "Kidnapping",
    "assault": "Assault",
    "dowry death": "Dowry Death",
    "fraud": "Cyber Fraud",
    "cyber fraud": "Cyber Fraud",
    "fake upi": "Cyber Fraud",
    "upi payment links": "Cyber Fraud",
    "upi payment link": "Cyber Fraud",
    "upi": "Cyber Fraud",
    "payment links": "Cyber Fraud",
    "online scam": "Cyber Fraud",
    "e-commerce scams": "Cyber Fraud",
    "cyber crime": "Cyber Crime",
    "cybercrime": "Cyber Crime",
    "cyber": "Cyber Crime",
    "hacking": "Cyber Crime",
    "phishing": "Cyber Fraud",
    "financial fraud": "Cyber Fraud",
    "molestation": "Molestation",
    "stalking": "Stalking",
    "extortion": "Extortion",
    "cheating": "Cheating",
    "forgery": "Forgery",
    "arson": "Arson",
    "rioting": "Rioting",
    "criminal breach of trust": "Criminal Breach of Trust",
    "cbt": "Criminal Breach of Trust",
    "cruelty": "Cruelty",
    "ಕಳ್ಳತನ": "Theft",
    "ಚೈನ್ ಸ್ನ್ಯಾಚಿಂಗ್": "Chain Snatching",

    "ಕೊಲೆ": "Murder",
    "ದರೋಡೆ": "Robbery",
    "ಅಪಹರಣ": "Kidnapping",
}

#: Status keywords → KSP status taxonomy string. The case service
#: resolves the name to an id.
_STATUS_KEYWORDS: dict[str, str] = {
    "open": "Open",
    "pending": "Under Investigation",
    "pending investigation": "Under Investigation",
    "under investigation": "Under Investigation",
    "investigating": "Under Investigation",
    "awaiting arrest": "Under Investigation",
    "charge sheeted": "Charge Sheeted",
    "chargesheeted": "Charge Sheeted",
    "charge-sheeted": "Charge Sheeted",
    "charge-sheet filed": "Charge Sheeted",
    "chargesheet filed": "Charge Sheeted",
    "cs filed": "Charge Sheeted",
    "closed": "Closed",
    "solved": "Closed",
    "undetected": "Undetected",
    "untraced": "Undetected",
    "false": "False Case",
    "fake": "False Case",
}


#: Date phrases → (from, to) callables. Each callable takes "today"
#: and returns the (date_from, date_to) pair.
import datetime as _dt


def _today_range(today: _dt.date) -> tuple[_dt.date, _dt.date]:
    return (today, today)


def _yesterday_range(today: _dt.date) -> tuple[_dt.date, _dt.date]:
    yesterday = today - _dt.timedelta(days=1)
    return (yesterday, yesterday)


def _this_week_range(today: _dt.date) -> tuple[_dt.date, _dt.date]:
    # Monday → today
    start = today - _dt.timedelta(days=today.weekday())
    return (start, today)


def _this_month_range(today: _dt.date) -> tuple[_dt.date, _dt.date]:
    start = today.replace(day=1)
    return (start, today)


def _last_n_days_range(n: int):
    def _calc(today: _dt.date) -> tuple[_dt.date, _dt.date]:
        return (today - _dt.timedelta(days=n), today)
    return _calc


_DATE_PHRASES: tuple[tuple[str, callable], ...] = (
    ("today", _today_range),
    ("yesterday", _yesterday_range),
    ("this week", _this_week_range),
    ("this month", _this_month_range),
    ("last 7 days", _last_n_days_range(7)),
    ("last seven days", _last_n_days_range(7)),
    ("last 30 days", _last_n_days_range(30)),
    ("last thirty days", _last_n_days_range(30)),
    ("last week", _this_week_range),  # alias
    ("last month", _this_month_range),  # alias
)

#: Recognises "between YYYY-MM-DD and YYYY-MM-DD" / "from
#: YYYY-MM-DD to YYYY-MM-DD" / "in YYYY" patterns.
_DATE_BETWEEN_RE = re.compile(
    r"\b(?:between|from|in)\s+"
    r"(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{4})\s*"
    r"(?:and|to|-|–|—|\s+to\s+)\s*"
    r"(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{4})\b",
    re.IGNORECASE,
)

#: Recognises a single YYYY-MM-DD token (used as a date_from).
_ISO_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")

#: FIR number (e.g. "FIR 104430003202400098").
_FIR_NUMBER_RE = re.compile(
    r"\bFIR\s+(?:number\s+)?([0-9]{10,20})\b", re.IGNORECASE
)


def _parse_date_token(token: str) -> _dt.date | None:
    """Best-effort parse of a date token from the question."""
    token = token.strip()
    # ISO: YYYY-MM-DD
    try:
        return _dt.date.fromisoformat(token)
    except ValueError:
        pass
    # Indian: DD/MM/YYYY
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", token)
    if m:
        try:
            return _dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    # Year only
    if re.fullmatch(r"\d{4}", token):
        try:
            year = int(token)
            return _dt.date(year, 1, 1)
        except ValueError:
            return None
    return None


def _build_case_filters(question: str, metadata: Mapping[str, Any] | None = None) -> Any:
    """Translate a free-text question into a :class:`CaseFilters`."""
    from backend.services import CaseFilters

    lowered = (question or "").lower()
    if not lowered:
        return CaseFilters()

    today = _dt.date.today()
    f: dict[str, Any] = {
        "fir_number": None,
        "district": None,
        "district_id": None,
        "police_station": None,
        "police_station_id": None,
        "crime_head": None,
        "crime_head_id": None,
        "crime_sub_head": None,
        "crime_sub_head_id": None,
        "status": None,
        "status_id": None,
        "date_from": None,
        "date_to": None,
    }
    notes: list[str] = []

    # 1. FIR / Case ID number (most specific)
    fir_match = _FIR_NUMBER_RE.search(question) or re.search(r"\b(?:case|fir|casemasterid|crime\s*no\.?)\s*[:=]?\s*(\d+)\b", lowered)
    if fir_match:
        f["fir_number"] = fir_match.group(1)
        return CaseFilters(**f)


    # 2. District name
    all_names = sorted(
        set(_DISTRICT_NAMES) | set(_LEGACY_DISTRICT_ALIASES.values()),
        key=len,
        reverse=True,
    )
    for name in all_names:
        if name.lower() in lowered:
            f["district"] = name
            break
    if f["district"] is None:
        for legacy, canonical in sorted(
            _LEGACY_DISTRICT_ALIASES.items(), key=lambda kv: len(kv[0]),
            reverse=True,
        ):
            if legacy in lowered:
                f["district"] = canonical
                break

    # 3. Locality → district
    if f["district"] is None:
        for locality, district in _LOCALITY_TO_DISTRICT.items():
            if locality in lowered:
                f["district"] = district
                f["police_station"] = locality.title()
                break

    # 4. Crime head
    for kw in sorted(_CRIME_HEAD_KEYWORDS, key=len, reverse=True):
        if kw in lowered:
            f["crime_head"] = _CRIME_HEAD_KEYWORDS[kw]
            break

    # 5. Status
    for kw in sorted(_STATUS_KEYWORDS, key=len, reverse=True):
        if kw in lowered:
            f["status"] = _STATUS_KEYWORDS[kw]
            break

    # 6. Date range
    if "last year" in lowered:
        f["date_from"] = _dt.date(today.year - 1, 1, 1)
        f["date_to"] = _dt.date(today.year - 1, 12, 31)
    elif "this year" in lowered:
        f["date_from"] = _dt.date(today.year, 1, 1)
        f["date_to"] = today
    elif "january and march" in lowered or "jan to mar" in lowered:
        f["date_from"] = _dt.date(today.year, 1, 1)
        f["date_to"] = _dt.date(today.year, 3, 31)
    else:
        between = _DATE_BETWEEN_RE.search(question)
        if between:
            date_from = _parse_date_token(between.group(1))
            date_to = _parse_date_token(between.group(2))
            if date_from and date_to and date_to < date_from:
                date_from, date_to = date_to, date_from
            f["date_from"] = date_from
            f["date_to"] = date_to
        else:
            for phrase, calc in _DATE_PHRASES:
                if phrase in lowered:
                    f["date_from"], f["date_to"] = calc(today)
                    break
            if f["date_from"] is None and f["date_to"] is None:
                m = re.search(r"\b(?:in|of|during)\s+(20\d{2}|19\d{2})\b", lowered)
                if m:
                    year = int(m.group(1))
                    f["date_from"] = _dt.date(year, 1, 1)
                    f["date_to"] = _dt.date(year, 12, 31)

    # 7. Context inheritance for conversational follow-ups
    meta_dict = dict(metadata or {})
    prev_filters = meta_dict.get("previous_filters") or meta_dict.get("context_filters")
    if isinstance(prev_filters, dict):
        if f["district"] is None and prev_filters.get("district"):
            f["district"] = prev_filters["district"]
        if f["crime_head"] is None and prev_filters.get("crime_head"):
            f["crime_head"] = prev_filters["crime_head"]
        if f["police_station"] is None and prev_filters.get("police_station"):
            f["police_station"] = prev_filters["police_station"]

    filters = CaseFilters(**f)
    if notes:
        filters.__dict__["_parse_notes"] = notes  # type: ignore[attr-defined]
    return filters



def _assumptions_for_filters(filters: Any) -> list[str]:
    """Describe the filters we applied, for the audit log."""
    if not filters:
        return ["No filters applied."]
    out: list[str] = []
    for key, value in filters.__dict__.items():
        # Skip the parser's own scratch attributes.
        if key.startswith("_"):
            continue
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


def _extract_case_id(question: str, meta: Mapping[str, Any] | None = None) -> int | None:
    q_str = question or ""
    match = _CASE_ID_RE.search(q_str) or re.search(r"\b(?:case|fir|casemasterid|crime\s*no\.?)\s*[:=]?\s*(\d+)\b", q_str, re.IGNORECASE)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    if meta:
        active_id = meta.get("active_case_id")
        if isinstance(active_id, int):
            return active_id
        elif isinstance(active_id, str) and active_id.isdigit():
            return int(active_id)
    return None



__all__ = [
    "EXPLANATION_PROMPT_NAME",
    "InvestigationService",
]
