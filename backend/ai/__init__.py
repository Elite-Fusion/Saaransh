"""
Saaransh AI — provider-independent AI layer.

This package holds every component that touches an LLM: the
provider abstraction, the prompt template loader, the chat
orchestrator, and (Phase 6) the AI investigation engine that turns
natural-language questions into safe, explainable database
operations.

Layering:

  * :mod:`backend.ai.models`     — domain models
    (``ChatRequest``, ``ChatResponse``).
  * :mod:`backend.ai.providers`  — provider abstraction and the
    concrete :class:`GeminiProvider` (Phase 5). Adding a new
    provider is one new file + one branch in
    :func:`backend.ai.providers.factory.get_provider`.
  * :mod:`backend.ai.services`   — :class:`PromptService`,
    :class:`ChatService`, and the Phase 6 investigation engine
    (:class:`IntentService`, :class:`SQLGenerationService`,
    :class:`SQLValidationService`, :class:`InvestigationService`).
    The only layer the routes depend on.
  * :mod:`backend.ai.prompts`    — Markdown templates, loaded at
    runtime. **No prompt is hardcoded in Python.**
  * :mod:`backend.ai.utils`      — small stdlib-only helpers
    (latency timer, token estimator).
  * :mod:`backend.ai.docs`       — planning documents.
  * :mod:`backend.ai.schemas`    — Pydantic v2 domain models for the
    investigation engine (Phase 6).

The public surface exported here is what the rest of the codebase
should import. Everything else is an implementation detail.
"""
from __future__ import annotations

from backend.ai.models import ChatMessage, ChatRequest, ChatResponse, ChatRole
from backend.ai.providers import (
    AIProvider,
    GeminiProvider,
    get_provider,
    reset_provider_cache,
)
from backend.ai.providers.errors import (
    AIConfigurationError,
    AIProviderError,
    AIRateLimitError,
    AIRequestError,
    AIResponseError,
    AITimeoutError,
    PromptNotFoundError,
    UnsupportedProviderError,
)
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
from backend.ai.services import (
    ChatService,
    IntentService,
    InvestigationService,
    PromptService,
    SQLGenerationService,
    SQLValidationService,
    get_prompt_service,
    reset_prompt_service_cache,
)
from backend.ai.services.exceptions import (
    ExecutionFailure,
    InvestigationError,
    PromptError,
    ProviderFailure,
    UnknownIntent,
    UnsafeSQL,
    ValidationFailure,
)

__all__ = [
    # models
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "ChatRole",
    # providers
    "AIProvider",
    "GeminiProvider",
    "get_provider",
    "reset_provider_cache",
    # services — Phase 5
    "ChatService",
    "PromptService",
    "get_prompt_service",
    "reset_prompt_service_cache",
    # services — Phase 6 (investigation engine)
    "IntentService",
    "SQLGenerationService",
    "SQLValidationService",
    "InvestigationService",
    # schemas — Phase 6
    "Intent",
    "IntentClassification",
    "GeneratedSQL",
    "ValidatedSQL",
    "EvidenceItem",
    "ExplanationBlock",
    "InvestigationResponse",
    "OperationType",
    "CaseSearchOperation",
    "DashboardAnalyticsOperation",
    "ExplainCaseOperation",
    "InvestigationSummaryOperation",
    "PlaceholderOperation",
    # errors
    "AIConfigurationError",
    "AIProviderError",
    "AIRateLimitError",
    "AIRequestError",
    "AIResponseError",
    "AITimeoutError",
    "UnsupportedProviderError",
    "PromptNotFoundError",
    # errors — Phase 6
    "InvestigationError",
    "UnknownIntent",
    "PromptError",
    "ProviderFailure",
    "UnsafeSQL",
    "ValidationFailure",
    "ExecutionFailure",
]
