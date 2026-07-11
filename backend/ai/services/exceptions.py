"""
Domain exceptions for the AI investigation engine.

These are the six exceptions the investigation pipeline may raise.
Grouping them in one module:

  * keeps imports tidy — every other AI service file does
    ``from backend.ai.services.exceptions import ...``;
  * makes it easy for the future route layer to map one base class
    (:class:`InvestigationError`) to a single 4xx/5xx envelope;
  * avoids a circular import between :mod:`sql_validation_service`,
    :mod:`sql_executor`, and :mod:`investigation_service`.

All six inherit from :class:`InvestigationError` so the route layer
can catch a single base class and decide how to render the failure.
The exception hierarchy mirrors the architecture diagram:

  InvestigationError            # base — catch in route handlers
  ├── UnknownIntent             # intent classifier gave up
  ├── PromptError               # PromptService could not find a file
  ├── ProviderFailure           # Gemini / chat service raised
  ├── UnsafeSQL                 # SQL validator rejected the statement
  │   └── ValidationFailure     # (alias) generic "validator said no"
  └── ExecutionFailure          # SQLAlchemy raised while running the SQL
"""
from __future__ import annotations


class InvestigationError(Exception):
    """Base class for every error raised by the AI investigation engine.

    The future route layer catches this single base class and decides
    how to render the failure (HTTP status, error envelope, etc.).
    Subclasses carry enough context to render a useful message without
    re-inspecting the traceback.
    """


class UnknownIntent(InvestigationError):
    """The intent classifier could not place the question in a known bucket.

    Raised after the LLM-based classifier returns ``UNKNOWN`` and the
    regex / keyword fallback also fails to match a category.
    """

    def __init__(self, question: str, *, reason: str = "") -> None:
        msg = f"Unknown intent for question: {question!r}"
        if reason:
            msg = f"{msg} ({reason})"
        super().__init__(msg)
        self.question = question
        self.reason = reason


class PromptError(InvestigationError):
    """The :class:`PromptService` could not load a named prompt.

    Distinct from :class:`ProviderFailure` because a missing prompt
    file is a programmer / configuration error, not a runtime
    provider failure. The route layer maps this to 500.
    """

    def __init__(self, prompt_name: str, *, original: Exception | None = None) -> None:
        msg = f"Prompt {prompt_name!r} could not be loaded."
        super().__init__(msg)
        self.prompt_name = prompt_name
        self.original = original


class ProviderFailure(InvestigationError):
    """The LLM provider raised an :class:`AIProviderError` subclass.

    The investigation service wraps every :class:`AIProviderError`
    (and its subclasses) into this single domain error so the route
    layer only ever has to catch one class. The original exception
    is preserved on ``self.original`` for diagnostics.
    """

    def __init__(
        self,
        message: str,
        *,
        original: Exception | None = None,
        provider: str | None = None,
    ) -> None:
        super().__init__(message)
        self.original = original
        self.provider = provider


class UnsafeSQL(InvestigationError):
    """The SQL validator rejected the statement.

    Carries a short, human-readable reason that the route layer can
    surface verbatim. The validator sets ``self.reason`` and
    ``self.sql`` (if available) so the audit log has enough
    context to reconstruct the failure.
    """

    def __init__(
        self,
        reason: str,
        *,
        sql: str | None = None,
        category: str | None = None,
    ) -> None:
        super().__init__(reason)
        self.reason = reason
        self.sql = sql
        self.category = category


class ValidationFailure(UnsafeSQL):
    """Generic catch-all for "the validator said no".

    A subclass of :class:`UnsafeSQL` so ``except UnsafeSQL`` catches
    it, but lets callers distinguish "we never reached validation"
    (None) from "we validated and the validator rejected" (this).
    """


class ExecutionFailure(InvestigationError):
    """The SQL executor raised while running the validated statement.

    The executor wraps every :class:`SQLAlchemyError` into this
    single domain error so the AI service layer does not import
    SQLAlchemy types.
    """

    def __init__(
        self,
        message: str,
        *,
        original: Exception | None = None,
        sql: str | None = None,
    ) -> None:
        super().__init__(message)
        self.original = original
        self.sql = sql


__all__ = [
    "InvestigationError",
    "UnknownIntent",
    "PromptError",
    "ProviderFailure",
    "UnsafeSQL",
    "ValidationFailure",
    "ExecutionFailure",
]
