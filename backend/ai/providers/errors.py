"""
AI provider exception hierarchy.

Every provider in :mod:`backend.ai.providers` translates SDK-specific
errors into one of the exceptions below before propagating them. Services
in :mod:`backend.ai.services` re-raise them unchanged so callers (HTTP
routes, scripts, tests) can catch a single base class and decide how to
render the failure.

Hierarchy::

    AIProviderError                  # base — catch this in route handlers
    ├── AIConfigurationError         # missing api key, bad model name, etc.
    ├── AIRequestError               # 4xx — bad request, context too long
    ├── AIRateLimitError             # 429 — provider throttled us
    ├── AITimeoutError               # request exceeded the configured timeout
    ├── AIResponseError              # 5xx — provider internal failure
    └── UnsupportedProviderError     # settings.ai_provider names a provider we
                                     # have not implemented yet

    PromptNotFoundError              # PromptService could not locate a
                                     # named .md file
"""
from __future__ import annotations


class AIProviderError(Exception):
    """Base class for every error raised by the AI provider layer.

    Catch this in route handlers to render a uniform 5xx response.
    Subclasses are mapped to specific HTTP status codes by the future
    ``/api/v1/ai/*`` routes (see ``backend/ai/docs/ai_api_plan.md``).
    """

    def __init__(self, message: str, *, provider: str | None = None) -> None:
        super().__init__(message)
        self.provider = provider

    def __repr__(self) -> str:  # pragma: no cover
        return f"{type(self).__name__}({self.args[0]!r}, provider={self.provider!r})"


class AIConfigurationError(AIProviderError):
    """Configuration problem detected at provider construction time.

    Examples: missing API key, unknown model name, missing prompt file
    on disk. Should be raised at startup, not on the first user request.
    """


class AIRequestError(AIProviderError):
    """The request itself is invalid (4xx-class).

    The provider rejected the input — context too long, unsupported
    parameter, malformed message. The caller should fix the input,
    not retry.
    """


class AIRateLimitError(AIProviderError):
    """Provider returned 429 (or its SDK equivalent).

    Tenacity's retry policy is allowed to retry on this class. After
    exhaustion the exception propagates to the caller.
    """


class AITimeoutError(AIProviderError):
    """The request exceeded the configured timeout.

    Retried by tenacity; propagated after ``ai_max_retries`` attempts.
    """


class AIResponseError(AIProviderError):
    """Provider returned 5xx (or its SDK equivalent).

    Typically transient; retried by tenacity.
    """


class UnsupportedProviderError(AIProviderError):
    """``settings.ai_provider`` names a provider that is not implemented
    in this phase.

    Only ``"gemini"`` is supported today. Claude, OpenAI, Groq, and
    OpenRouter will be added in later phases — see
    ``backend/ai/docs/ai_api_plan.md``.
    """


class PromptNotFoundError(Exception):
    """``PromptService`` could not find a prompt file matching ``name``.

    Distinct from :class:`AIProviderError` because it is a programmer
    error (wrong file name), not a runtime provider failure.
    """

    def __init__(self, name: str, *, prompts_dir: str | None = None) -> None:
        loc = f" (in {prompts_dir})" if prompts_dir else ""
        super().__init__(f"Prompt {name!r} not found{loc}")
        self.name = name
        self.prompts_dir = prompts_dir
