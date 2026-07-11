"""
AI services — provider-agnostic, FastAPI-independent.

This package contains the orchestrators that sit between the
route layer (added in Phase 6+) and the provider layer. They
are pure-Python classes, instantiated and injected explicitly:

  * :class:`PromptService` — loads and renders prompt templates.
  * :class:`ChatService` — sends a single chat request through a
    provider and returns a structured :class:`ChatResponse`.
  * :class:`IntentService` — Phase 6. Classifies a question into
    one of six intent buckets.
  * :class:`SQLGenerationService` — Phase 6. Asks the LLM for a
    parameterised SQL statement.
  * :class:`SQLValidationService` — Phase 6. Runs the allowlist
    check on the generated SQL.
  * :class:`InvestigationService` — Phase 6. End-to-end orchestrator
    that composes the four above plus an injected
    :class:`AIQueryService` and a :class:`CaseService` /
    :class:`AnalyticsService`.

Nothing in this package imports ``fastapi`` or ``starlette`` —
this is enforced by ``backend/tests/test_ai/test_ai_independence.py``.

The exceptions live in :mod:`backend.ai.services.exceptions` so
every other module can do
``from backend.ai.services.exceptions import UnsafeSQL``.
"""
from backend.ai.services.chat_service import ChatService
from backend.ai.services.exceptions import (
    ExecutionFailure,
    InvestigationError,
    PromptError,
    ProviderFailure,
    UnknownIntent,
    UnsafeSQL,
    ValidationFailure,
)
from backend.ai.services.intent_service import (
    INTENT_PROMPT_NAME,
    IntentService,
)
from backend.ai.services.investigation_service import (
    EXPLANATION_PROMPT_NAME,
    InvestigationService,
)
from backend.ai.services.prompt_service import (
    PromptService,
    get_prompt_service,
    reset_prompt_service_cache,
)
from backend.ai.services.sql_generation_service import (
    SQL_PROMPT_NAME,
    SQLGenerationService,
)
from backend.ai.services.sql_validation_service import (
    ALLOWED_CLAUSE_TOKENS,
    DEFAULT_FORBIDDEN_TOKENS,
    DEFAULT_FORBIDDEN_VERBS,
    DEFAULT_READ_ONLY_VERBS,
    SQLValidationService,
)

__all__ = [
    # Phase 5
    "ChatService",
    "PromptService",
    "get_prompt_service",
    "reset_prompt_service_cache",
    # Phase 6 — investigation engine
    "IntentService",
    "SQLGenerationService",
    "SQLValidationService",
    "InvestigationService",
    "INTENT_PROMPT_NAME",
    "SQL_PROMPT_NAME",
    "EXPLANATION_PROMPT_NAME",
    "ALLOWED_CLAUSE_TOKENS",
    "DEFAULT_FORBIDDEN_TOKENS",
    "DEFAULT_FORBIDDEN_VERBS",
    "DEFAULT_READ_ONLY_VERBS",
    # Phase 6 — exceptions
    "InvestigationError",
    "UnknownIntent",
    "PromptError",
    "ProviderFailure",
    "UnsafeSQL",
    "ValidationFailure",
    "ExecutionFailure",
]
