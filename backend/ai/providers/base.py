"""
Abstract AI provider — every concrete provider (Gemini today; Claude,
OpenAI, Groq, OpenRouter in later phases) implements this interface.

The contract is the single point of indirection between
:mod:`backend.ai.services` and any specific LLM SDK. Services depend
on this class, never on a concrete provider or an SDK import.

Design rules (enforced by the tests in
:mod:`backend.tests.test_ai.test_ai_independence`):

  * All public methods are **synchronous** (``def``, not ``async def``).
    Concurrency is the route layer's job; the provider is a plain
    callable. This keeps the test surface small (no ``asyncio``,
    no ``pytest-asyncio``).
  * All exceptions raised are subclasses of
    :class:`backend.ai.providers.errors.AIProviderError`. Callers
    catch that base class and decide how to render the failure.
  * No ``fastapi`` / ``starlette`` import anywhere in the provider
    tree. The provider does not know it is being called from an
    HTTP request.
  * Every call is logged with at minimum: ``provider``, ``model``,
    ``latency_ms``, ``status`` (``"success"`` / ``"failure"``),
    and on failure the ``error_type`` (the exception class name).
  * No prompt content is logged (CLAUDE.md: "Never log API keys"
    generalises — sensitive user input is also off-limits).
"""
from __future__ import annotations

import abc
import logging
from typing import TYPE_CHECKING

from backend.ai.providers.errors import AIProviderError
from backend.ai.utils.latency import LatencyTimer

if TYPE_CHECKING:
    from backend.ai.models.chat import ChatRequest, ChatResponse


class AIProvider(abc.ABC):
    """Provider-agnostic interface every LLM backend implements.

    A provider is configured once at construction time (api key,
    model, timeout, retry policy) and is then a thin callable. All
    per-call state is on the :class:`~backend.ai.models.chat.ChatRequest`
    and :class:`~backend.ai.models.chat.ChatResponse` objects.

    Concrete providers should expose ``name`` and ``model`` as
    class attributes or instance attributes so the logging layer
    can stamp every log line with which backend produced it.
    """

    #: Provider name surfaced on every ``ChatResponse`` and log line
    #: (e.g. ``"gemini"``, ``"claude"``, ``"openai"``).
    name: str = "abstract"

    #: Default model used when the caller does not override it.
    default_model: str = ""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout: float,
        max_retries: int,
        logger: logging.Logger | None = None,
    ) -> None:
        if not api_key:
            raise ValueError(
                f"{type(self).__name__}: api_key is required "
                f"(check settings.{self.name}_api_key)"
            )
        if not model:
            raise ValueError(
                f"{type(self).__name__}: model is required "
                f"(check settings.{self.name}_model)"
            )
        if timeout <= 0:
            raise ValueError(f"{type(self).__name__}: timeout must be > 0 seconds")
        if max_retries < 0:
            raise ValueError(f"{type(self).__name__}: max_retries must be >= 0")

        self._api_key = api_key
        self.model = model
        self._timeout = float(timeout)
        self._max_retries = int(max_retries)
        self.logger = logger or logging.getLogger(
            f"backend.ai.providers.{self.name}"
        )

    # ------------------------------------------------------------------
    # Public surface
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def chat(self, request: "ChatRequest") -> "ChatResponse":
        """Run a single chat call and return the result.

        Implementations must:

          * validate the request before any network IO;
          * run with the configured timeout;
          * retry transient failures (429, 5xx, timeout) up to
            ``self._max_retries`` times with exponential backoff;
          * translate every SDK-specific exception into a
            :class:`AIProviderError` subclass before returning;
          * log the start and the finish (success or failure) at
            ``INFO`` level.

        Args:
            request: The :class:`~backend.ai.models.chat.ChatRequest`
                to send. The provider may use ``request.system_prompt``,
                ``request.temperature``, ``request.max_output_tokens``,
                and ``request.messages``.

        Returns:
            A :class:`~backend.ai.models.chat.ChatResponse` with
            ``latency_ms`` filled in.

        Raises:
            AIProviderError: Any failure the provider could not
                recover from. The exception is always a subclass of
                the base class.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def count_tokens(self, text: str) -> int:
        """Return the number of tokens ``text`` would consume.

        Implementations should prefer the provider's native
        count-tokens endpoint when one exists. If the provider does
        not expose one, fall back to
        :func:`backend.ai.utils.token_estimator.estimate_tokens`.

        Args:
            text: The string to measure. Empty strings return ``0``.

        Returns:
            A non-negative integer.
        """
        raise NotImplementedError

    def health_check(self) -> bool:
        """Return ``True`` if the provider is reachable.

        The default implementation does not call the network — it
        is a cheap liveness probe. Concrete providers may override
        it with a minimal API call, but should cache the result
        for at most a few seconds to keep the cost down.
        """
        return bool(self._api_key) and bool(self.model)

    # ------------------------------------------------------------------
    # Internal helpers shared by concrete providers
    # ------------------------------------------------------------------

    def _start_timer(self) -> LatencyTimer:
        """Start a latency timer. Subclasses call this in ``chat()``."""
        return LatencyTimer().start()

    def _log_call_start(self, request: "ChatRequest") -> None:
        """Emit the start-of-call log line. Never logs prompt content."""
        self.logger.info(
            "ai_call_start provider=%s model=%s messages=%d "
            "max_output_tokens=%d temperature=%.2f",
            self.name,
            self.model,
            len(request.messages),
            request.max_output_tokens,
            request.temperature,
        )

    def _log_call_success(
        self,
        latency_ms: int,
        *,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
    ) -> None:
        """Emit the success log line."""
        self.logger.info(
            "ai_call_success provider=%s model=%s latency_ms=%d "
            "prompt_tokens=%s completion_tokens=%s",
            self.name,
            self.model,
            latency_ms,
            prompt_tokens if prompt_tokens is not None else "?",
            completion_tokens if completion_tokens is not None else "?",
        )

    def _log_call_failure(
        self,
        latency_ms: int,
        error: BaseException,
    ) -> None:
        """Emit the failure log line. Never logs prompt content."""
        self.logger.warning(
            "ai_call_failure provider=%s model=%s latency_ms=%d "
            "error_type=%s error=%s",
            self.name,
            self.model,
            latency_ms,
            type(error).__name__,
            str(error)[:200],
        )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<{type(self).__name__} name={self.name!r} "
            f"model={self.model!r} timeout={self._timeout}s "
            f"max_retries={self._max_retries}>"
        )


__all__ = ["AIProvider", "AIProviderError"]
