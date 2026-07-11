"""
Pydantic v2 domain models for the AI investigation engine.

These are the public types the AI service layer produces and the
future route layer serialises. They are deliberately separate from
the AI provider's own :class:`~backend.ai.models.chat.ChatRequest` /
:class:`~backend.ai.models.chat.ChatResponse` so a refactor of the
provider layer cannot accidentally change the investigation API.

The Pydantic v2 ``model_config = ConfigDict(extra="forbid")`` guard
on every model means a future caller cannot smuggle unknown fields
into a route response — important when the response is shown to
police officers and audited under the RBAC rules of Phase 10.

All models are **domain models**, not FastAPI request/response
models. The future route layer (Phase 7+) wraps each in a standard
envelope (``{"data": ..., "meta": ...}``) — see
:file:`backend/ai/docs/ai_api_plan.md`.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------


class Intent(str, Enum):
    """The six buckets the intent classifier can assign a question to.

    * ``CASE_SEARCH``            — find FIRs / cases by filter.
    * ``DASHBOARD_ANALYTICS``    — aggregations, distributions, counts.
    * ``SIMILAR_CASES``          — placeholder for Phase 7 vector search.
    * ``INVESTIGATION_SUMMARY``  — multi-case brief for an officer.
    * ``EXPLAIN_CASE``           — narrative about a single case id.
    * ``UNKNOWN``                — classifier could not place the question.
    """

    CASE_SEARCH = "case_search"
    DASHBOARD_ANALYTICS = "dashboard_analytics"
    SIMILAR_CASES = "similar_cases"
    INVESTIGATION_SUMMARY = "investigation_summary"
    EXPLAIN_CASE = "explain_case"
    UNKNOWN = "unknown"


# Allowed SQL verbs for the LLM output. Mirrors the executor's
# READ_ONLY_VERBS but re-declared here so the schema is self-contained.
ALLOWED_SQL_VERBS: tuple[str, ...] = ("SELECT", "WITH")


# ---------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------


class IntentClassification(BaseModel):
    """The output of :class:`IntentService.classify`.

    Carries the label, a one-sentence ``reasoning`` field for the
    audit log, and the ``raw_response`` from the LLM (truncated to
    500 chars) so a regression in the classifier is reproducible.
    """

    model_config = ConfigDict(extra="forbid")

    intent: Intent = Field(..., description="The classified intent.")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Classifier's self-reported confidence (0..1).",
    )
    reasoning: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="One-sentence rationale for the label.",
    )
    raw_response: str = Field(
        default="",
        max_length=2000,
        description="Truncated LLM response that produced the classification.",
    )


# ---------------------------------------------------------------------
# SQL generation
# ---------------------------------------------------------------------


class GeneratedSQL(BaseModel):
    """A SQL statement produced by the LLM, before validation.

    The LLM is asked to return a JSON object shaped exactly like this.
    ``params`` uses named bind parameters so the validator can check
    that every ``:name`` reference is bound. ``tables`` is the LLM's
    self-reported list of referenced tables — the validator ignores
    it (it parses the SQL itself) but the audit log keeps it.
    """

    model_config = ConfigDict(extra="forbid")

    sql: str = Field(
        default="",
        description=(
            "The SELECT (or WITH ... SELECT) statement. May be empty "
            "when the LLM explicitly refuses the request — the "
            "generator converts that to UnsafeSQL."
        ),
    )
    params: dict[Any, Any] = Field(
        default_factory=dict,
        description=(
            "Named bind parameters. Every :name reference in ``sql`` "
            "MUST be present here as a key (without the leading ':'). "
            "Keys are checked by the validator; non-string keys raise "
            ":class:`ValidationFailure` with ``category='bad_param'``."
        ),
    )
    tables: list[str] = Field(
        default_factory=list,
        description="Tables the LLM believes the statement references.",
    )
    estimated_rows: Literal["low", "medium", "high", "unknown"] = Field(
        default="unknown",
        description="LLM's self-reported row estimate.",
    )
    notes: str = Field(
        default="",
        max_length=1000,
        description="Free-text caveats the LLM wants to surface.",
    )


class ValidatedSQL(BaseModel):
    """A SQL statement that has passed the validator.

    Carries the original :class:`GeneratedSQL` plus a normalised
    parameter set. The executor accepts this shape directly.
    """

    model_config = ConfigDict(extra="forbid")

    sql: str = Field(..., min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)
    tables: list[str] = Field(default_factory=list)
    estimated_rows: Literal["low", "medium", "high", "unknown"] = "unknown"
    notes: str = Field(default="", max_length=1000)


# ---------------------------------------------------------------------
# Evidence and explanation
# ---------------------------------------------------------------------


class EvidenceItem(BaseModel):
    """A single piece of evidence that grounds an answer.

    The shape mirrors the example in
    :file:`backend/ai/prompts/explanation_prompt.md` — the LLM emits
    one ``EvidenceItem`` per cited row.
    """

    model_config = ConfigDict(extra="forbid")

    case_id: int | None = Field(
        default=None,
        description="The CaseMaster.CaseMasterID, if applicable.",
    )
    fir_number: str | None = Field(
        default=None,
        max_length=64,
        description="The CaseMaster.CrimeNo (FIR number), if known.",
    )
    label: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Short human-readable description of the cited row.",
    )


class ExplanationBlock(BaseModel):
    """The explanation section of an :class:`InvestigationResponse`.

    Carries a headline ``summary``, a list of :class:`EvidenceItem`,
    the reasoning chain in ``why``, a self-reported ``confidence``
    (high / medium / low) plus a numeric 0..1 score, and a list of
    short caveats the officer should know about.
    """

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(..., min_length=1, max_length=2000)
    evidence: list[EvidenceItem] = Field(
        default_factory=list,
        max_length=50,
        description="Cited rows. At least one when the answer is grounded.",
    )
    why: str = Field(..., min_length=1, max_length=2000)
    confidence: Literal["high", "medium", "low"] = Field(default="medium")
    confidence_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Numeric translation of the confidence label.",
    )
    confidence_reason: str = Field(
        default="",
        max_length=500,
    )
    caveats: list[str] = Field(default_factory=list, max_length=20)


# ---------------------------------------------------------------------
# Top-level response
# ---------------------------------------------------------------------


class OperationType(str, Enum):
    """The kind of work the investigation service performed.

    * ``SERVICE``     — the answer came from an existing service method.
    * ``SQL``         — the LLM generated SQL that the executor ran.
    * ``PLACEHOLDER`` — a future phase will implement this (similar cases).
    * ``NONE``        — the intent was UNKNOWN; no work was done.
    """

    SERVICE = "service"
    SQL = "sql"
    PLACEHOLDER = "placeholder"
    NONE = "none"


class InvestigationResponse(BaseModel):
    """The structured response of the AI investigation engine.

    Every field is ``extra="forbid"`` so a future caller cannot smuggle
    unknown keys into the JSON serialised by the route layer. The
    response is intentionally complete — no opaque blobs.
    """

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., min_length=1, max_length=128)
    intent: Intent
    operation: OperationType
    reasoning: str = Field(..., min_length=1, max_length=1000)
    executed_operation: str = Field(..., min_length=1, max_length=500)
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Numeric confidence in the answer (0..1).",
    )
    assumptions: list[str] = Field(default_factory=list, max_length=20)
    supporting_evidence: list[EvidenceItem] = Field(
        default_factory=list,
        max_length=50,
    )
    explanation: ExplanationBlock | None = None
    raw_sql: str | None = None
    raw_params: dict[str, Any] | None = None
    row_count: int | None = Field(default=None, ge=0)
    columns: list[str] | None = None
    placeholder: dict[str, Any] | None = None


# ---------------------------------------------------------------------
# Operation descriptors (returned by the intent router)
# ---------------------------------------------------------------------


class CaseSearchOperation(BaseModel):
    """The intent router chose :class:`Intent.CASE_SEARCH`."""

    model_config = ConfigDict(extra="forbid")
    filters: dict[str, Any] = Field(default_factory=dict)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_field: str = Field(default="crime_registered_date")
    sort_order: Literal["asc", "desc"] = "desc"


class DashboardAnalyticsOperation(BaseModel):
    """The intent router chose :class:`Intent.DASHBOARD_ANALYTICS`."""

    model_config = ConfigDict(extra="forbid")
    metric: Literal["summary", "monthly_trends", "crime_head", "district"] = "summary"
    year: int | None = Field(default=None, ge=1900, le=2100)
    district_id: int | None = None


class ExplainCaseOperation(BaseModel):
    """The intent router chose :class:`Intent.EXPLAIN_CASE`."""

    model_config = ConfigDict(extra="forbid")
    case_id: int = Field(..., ge=1)


class InvestigationSummaryOperation(BaseModel):
    """The intent router chose :class:`Intent.INVESTIGATION_SUMMARY`."""

    model_config = ConfigDict(extra="forbid")
    case_id: int = Field(..., ge=1)
    similar_case_ids: list[int] = Field(default_factory=list)


class PlaceholderOperation(BaseModel):
    """The intent router chose :class:`Intent.SIMILAR_CASES` (Phase 7+)."""

    model_config = ConfigDict(extra="forbid")
    feature: Literal["similar_cases"] = "similar_cases"
    case_id: int | None = None
    message: str = "Similar-case search is scheduled for Phase 7."


__all__ = [
    "ALLOWED_SQL_VERBS",
    "CaseSearchOperation",
    "DashboardAnalyticsOperation",
    "EvidenceItem",
    "ExplainCaseOperation",
    "ExplanationBlock",
    "GeneratedSQL",
    "Intent",
    "IntentClassification",
    "InvestigationResponse",
    "InvestigationSummaryOperation",
    "OperationType",
    "PlaceholderOperation",
    "ValidatedSQL",
]
