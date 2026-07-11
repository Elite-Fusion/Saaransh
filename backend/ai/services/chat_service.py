"""
ChatService — the single orchestrator that the future route layer
calls.

The service is the only place in the codebase that knows both
how to render a named prompt and how to call the provider. The
goal is to keep the route layer dumb: it deserialises a request
body, hands it to :class:`ChatService`, and serialises the
:class:`ChatResponse` it gets back. No business logic in the
route.

Two entry points:

  * :meth:`chat(request)` — pass a pre-built
    :class:`ChatRequest` straight through to the provider.
    Useful for code paths that build the messages list themselves
    (a future similarity search, a graph traversal, etc.).

  * :meth:`chat_with_prompt(name, user_message, **vars)` — load
    + render a named prompt, build a single-user-message
    :class:`ChatRequest`, and send it. This is the
    "give me an answer from a named prompt template" flow
    the future ``/api/v1/ai/*`` routes will use.

Both methods:

  * take a :class:`PromptService` and an :class:`AIProvider` in
    the constructor (no module-level singletons in the hot
    path — only the convenience :func:`get_provider` and
    :func:`get_prompt_service` use a cache);
  * stamp the response with the provider's ``name`` and
    ``model`` so log lines are correlatable;
  * propagate provider exceptions unchanged — the caller
    decides how to render them.
"""
from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from backend.ai.providers.base import AIProvider
from backend.ai.services.prompt_service import PromptService

if TYPE_CHECKING:
    from backend.ai.models.chat import ChatRequest, ChatResponse


class ChatService:
    """Provider-agnostic, FastAPI-independent chat orchestrator.

    Args:
        provider: The :class:`AIProvider` to send the request
            through. Typically obtained from
            :func:`backend.ai.providers.get_provider`.
        prompt_service: The :class:`PromptService` that loads
            named prompt templates. Typically obtained from
            :func:`backend.ai.services.get_prompt_service`.
        logger: Optional :class:`logging.Logger` to record
            per-call events. Defaults to a module-level logger.
    """

    def __init__(
        self,
        *,
        provider: AIProvider,
        prompt_service: PromptService,
        logger: logging.Logger | None = None,
    ) -> None:
        self._provider = provider
        self._prompts = prompt_service
        self.logger = logger or logging.getLogger("backend.ai.services.chat_service")

    # ------------------------------------------------------------------
    # Public surface
    # ------------------------------------------------------------------

    def chat(self, request: "ChatRequest") -> "ChatResponse":
        """Send a pre-built :class:`ChatRequest` through the provider.

        Args:
            request: The :class:`ChatRequest`. ``system_prompt``,
                ``messages``, ``temperature``, ``max_output_tokens``,
                and ``metadata`` are all read.

        Returns:
            A :class:`ChatResponse` with ``latency_ms`` filled in
            by the service (it re-times the call so the value
            reflects the *whole* ``chat`` call, including the
            provider's own internal timing).

        Raises:
            AIProviderError: Any provider-level failure. Propagated
                unchanged; the route layer renders the HTTP
                response.
        """
        self.logger.info(
            "chat_service_call_start provider=%s model=%s messages=%d",
            self._provider.name,
            self._provider.model,
            len(request.messages),
        )
        response = self._provider.chat(request)
        self.logger.info(
            "chat_service_call_success provider=%s model=%s "
            "latency_ms=%d prompt_tokens=%s completion_tokens=%s",
            self._provider.name,
            self._provider.model,
            response.latency_ms,
            response.prompt_tokens if response.prompt_tokens is not None else "?",
            response.completion_tokens
            if response.completion_tokens is not None
            else "?",
        )
        return response

    def chat_with_prompt(
        self,
        prompt_name: str,
        user_message: str,
        *,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
        **prompt_vars: Any,
    ) -> "ChatResponse":
        """Render a named prompt, build a request, and call the provider.

        Args:
            prompt_name: The prompt file stem (e.g. ``"sql_prompt"``).
                The :class:`PromptService` will load and render
                ``backend/ai/prompts/{prompt_name}.md``.
            user_message: The user-side text appended after the
                rendered prompt. Becomes a single
                :class:`ChatMessage` with role ``user``.
            temperature: Optional override for the request's
                ``temperature``. Defaults to the request model's
                value (0.2).
            max_output_tokens: Optional override for the request's
                ``max_output_tokens``. Defaults to the model value
                (1024).
            metadata: Optional metadata dict copied onto the
                request. Useful for tagging the call with a
                request id, user id, etc. — never for PII.
            **prompt_vars: Keyword arguments substituted into the
                prompt template.

        Returns:
            A :class:`ChatResponse` with the provider's answer
            in ``content`` and ``latency_ms`` filled in.
        """
        from backend.ai.models.chat import (
            ChatMessage,
            ChatRequest,
            ChatRole,
        )

        rendered = self._prompts.render(prompt_name, **prompt_vars)

        request_kwargs: dict[str, Any] = {
            "system_prompt": rendered,
            "messages": [ChatMessage(role=ChatRole.USER, content=user_message)],
            "metadata": dict(metadata or {}),
        }
        if temperature is not None:
            request_kwargs["temperature"] = temperature
        if max_output_tokens is not None:
            request_kwargs["max_output_tokens"] = max_output_tokens

        request = ChatRequest(**request_kwargs)
        return self.chat(request)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def provider(self) -> AIProvider:
        """The provider this service delegates to."""
        return self._provider

    @property
    def prompt_service(self) -> PromptService:
        """The prompt service this service reads templates from."""
        return self._prompts

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"ChatService(provider={self._provider.name!r}, "
            f"model={self._provider.model!r})"
        )


__all__ = ["ChatService"]
