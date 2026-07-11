"""
Google Gemini provider — the only concrete provider in Phase 5.

Uses the new unified ``google-genai`` SDK (``from google import genai``).
The class is the only place in the codebase that imports the SDK;
the rest of the AI layer talks to :class:`AIProvider`.

Retry policy is implemented with ``tenacity``. The provider retries
on transient failures (HTTP 429, HTTP 5xx, ``TimeoutError``) with
exponential backoff. After exhaustion, the original SDK exception
is translated to a domain
:class:`~backend.ai.providers.errors.AIProviderError` subclass.

The provider is **fully synchronous** — ``generate_content`` is a
blocking call. The FastAPI threadpool handles concurrency at the
HTTP layer.
"""
from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from backend.ai.providers.base import AIProvider
from backend.ai.providers.errors import (
    AIConfigurationError,
    AIProviderError,
    AIRateLimitError,
    AIRequestError,
    AIResponseError,
    AITimeoutError,
)
from backend.ai.utils.token_estimator import estimate_tokens

if TYPE_CHECKING:
    from backend.ai.models.chat import ChatRequest, ChatResponse


class GeminiProvider(AIProvider):
    """AIProvider implementation for Google Gemini (google-genai SDK).

    The provider is constructed with the four required settings from
    :class:`backend.config.settings.Settings` and a single
    :class:`logging.Logger`. The SDK client is created lazily on
    the first call so construction never triggers a network round
    trip — that means ``Settings`` validation can catch a missing
    API key at import time without paying a startup cost.

    SDK errors are translated to the domain exception hierarchy
    defined in :mod:`backend.ai.providers.errors`. Callers
    (:class:`~backend.ai.services.chat_service.ChatService` and the
    future route layer) re-raise them unchanged.
    """

    name: str = "gemini"
    default_model: str = "gemini-2.0-flash"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout: float,
        max_retries: int,
        logger: logging.Logger | None = None,
        # Test hook: the SDK client builder is injected so unit tests
        # can supply a mock without monkey-patching the SDK.
        client_factory: Any | None = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            model=model,
            timeout=timeout,
            max_retries=max_retries,
            logger=logger,
        )
        # Lazy client; built on first call.
        self._client: Any | None = None
        self._client_factory = client_factory

    # ------------------------------------------------------------------
    # Public surface
    # ------------------------------------------------------------------

    def chat(self, request: "ChatRequest") -> "ChatResponse":
        """Send a chat request to Gemini and return the response.

        Args:
            request: The :class:`ChatRequest` to send. The provider
                maps ``request.messages`` to ``contents``,
                ``request.system_prompt`` to ``system_instruction``,
                ``request.temperature`` to ``config.temperature``,
                and ``request.max_output_tokens`` to
                ``config.max_output_tokens``.

        Returns:
            A :class:`ChatResponse` populated from the SDK response.

        Raises:
            AIConfigurationError: The client could not be built
                (e.g. SDK import failure).
            AIRequestError: The request was malformed (4xx-class).
            AIRateLimitError: 429 from the SDK; retried automatically
                but raised if it persists.
            AITimeoutError: The call exceeded ``self._timeout``.
            AIResponseError: The SDK returned a 5xx-class error.
        """
        # The actual google-genai imports are lazy and live in
        # ``_get_client`` / ``_build_sdk_payload`` so the module is
        # importable even when the SDK is not installed.
        self._log_call_start(request)
        timer = self._start_timer()

        contents, config = self._build_sdk_payload(request)
        client = self._get_client()

        # Translate every SDK exception to a domain error *inside*
        # the retry loop so tenacity only ever sees AIProviderError
        # subclasses. This keeps the retry policy single-typed.
        def _call_once() -> Any:
            try:
                return client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                )
            except AIProviderError:
                raise
            except Exception as exc:
                raise self._translate_sdk_error(exc) from exc

        try:
            sdk_response = self._call_with_retry(_call_once)
        except AIProviderError as exc:
            latency = timer.elapsed_ms()
            self._log_call_failure(latency, exc)
            raise

        latency = timer.elapsed_ms()
        response = self._build_response(sdk_response, latency=request.metadata)
        self._log_call_success(
            latency,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
        )
        return response

    def count_tokens(self, text: str) -> int:
        """Count tokens using the SDK when possible, else the heuristic.

        Args:
            text: The string to measure. Empty strings return ``0``.

        Returns:
            A non-negative integer.
        """
        if not text:
            return 0
        try:
            client = self._get_client()
        except AIConfigurationError:
            return estimate_tokens(text)
        try:
            response = client.models.count_tokens(model=self.model, contents=text)
            total = getattr(response, "total_tokens", None)
            if isinstance(total, int) and total >= 0:
                return total
        except Exception:  # pragma: no cover (defensive)
            self.logger.debug("count_tokens SDK call failed; using estimator")
        return estimate_tokens(text)

    # ------------------------------------------------------------------
    # Payload construction
    # ------------------------------------------------------------------

    def _build_sdk_payload(self, request: "ChatRequest") -> tuple[list[Any], Any]:
        """Translate a ``ChatRequest`` into the SDK's native types.

        Returns:
            A ``(contents, config)`` pair. ``contents`` is a list
            suitable for the ``contents=`` kwarg of
            ``client.models.generate_content``. ``config`` is a
            ``GenerateContentConfig`` instance.
        """
        from google.genai import types as genai_types

        contents: list[Any] = []
        for msg in request.messages:
            role = self._map_role_to_gemini(msg.role)
            contents.append(
                genai_types.Content(
                    role=role,
                    parts=[genai_types.Part(text=msg.content)],
                )
            )

        config_kwargs: dict[str, Any] = {
            "temperature": float(request.temperature),
            "max_output_tokens": int(request.max_output_tokens),
        }
        if request.system_prompt:
            config_kwargs["system_instruction"] = request.system_prompt

        config = genai_types.GenerateContentConfig(**config_kwargs)
        return contents, config

    @staticmethod
    def _map_role_to_gemini(role: Any) -> str:
        """Map a :class:`ChatRole` to Gemini's role name.

        Gemini uses ``"user"`` and ``"model"`` (not ``"assistant"``).
        ``"system"`` is conveyed via the config's
        ``system_instruction`` and is therefore skipped here.
        ``"tool"`` is unsupported by the chat path used in Phase 5
        and is folded into ``"user"`` for forward compatibility.
        """
        value = getattr(role, "value", str(role))
        if value == "assistant":
            return "model"
        if value == "system":
            return "user"
        if value == "tool":
            return "user"
        return "user"

    # ------------------------------------------------------------------
    # Response construction
    # ------------------------------------------------------------------

    def _build_response(
        self,
        sdk_response: Any,
        *,
        latency: dict[str, Any] | None = None,
    ) -> "ChatResponse":
        """Translate a ``GenerateContentResponse`` into a ``ChatResponse``."""
        from backend.ai.models.chat import ChatResponse

        content = self._extract_text(sdk_response)
        finish_reason = self._extract_finish_reason(sdk_response)
        usage = self._extract_usage(sdk_response)

        meta: dict[str, Any] = dict(latency or {})
        meta.setdefault("provider", self.name)
        meta.setdefault("model", self.model)

        return ChatResponse(
            provider=self.name,
            model=self.model,
            content=content,
            finish_reason=finish_reason,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
            latency_ms=0,  # filled by the caller from the LatencyTimer
            metadata=meta,
        )

    @staticmethod
    def _extract_text(sdk_response: Any) -> str:
        """Pull the assistant text from a ``GenerateContentResponse``."""
        # The SDK exposes `.text` on the response, and a `.candidates`
        # list with `.content.parts[].text`. Try both.
        text_attr = getattr(sdk_response, "text", None)
        if isinstance(text_attr, str) and text_attr:
            return text_attr
        candidates = getattr(sdk_response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            if content is None:
                continue
            parts = getattr(content, "parts", None) or []
            for part in parts:
                t = getattr(part, "text", None)
                if isinstance(t, str) and t:
                    return t
        return ""

    @staticmethod
    def _extract_finish_reason(sdk_response: Any) -> str | None:
        candidates = getattr(sdk_response, "candidates", None) or []
        if not candidates:
            return None
        first = candidates[0]
        reason = getattr(first, "finish_reason", None)
        if reason is None:
            return None
        return getattr(reason, "name", str(reason))

    @staticmethod
    def _extract_usage(sdk_response: Any) -> dict[str, int | None]:
        meta = getattr(sdk_response, "usage_metadata", None)
        if meta is None:
            return {"prompt_tokens": None, "completion_tokens": None, "total_tokens": None}
        return {
            "prompt_tokens": getattr(meta, "prompt_token_count", None),
            "completion_tokens": getattr(meta, "candidates_token_count", None),
            "total_tokens": getattr(meta, "total_token_count", None),
        }

    # ------------------------------------------------------------------
    # SDK client management
    # ------------------------------------------------------------------

    def _get_client(self) -> Any:
        """Return the cached SDK client, building it on first call."""
        if self._client is not None:
            return self._client
        try:
            from google import genai
        except ImportError as exc:  # pragma: no cover (env problem)
            raise AIConfigurationError(
                "google-genai is not installed. Run "
                "`pip install google-genai` in the backend venv."
            ) from exc
        if self._client_factory is not None:
            self._client = self._client_factory(api_key=self._api_key)
        else:
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    # ------------------------------------------------------------------
    # Retry policy
    # ------------------------------------------------------------------

    def _retrying(self) -> Retrying:
        """Build the tenacity retry policy for this provider.

        Retries on the domain errors that represent transient
        conditions:

          * :class:`AIRateLimitError` — HTTP 429 from the SDK;
          * :class:`AIResponseError` — HTTP 5xx or generic SDK
            server failure;
          * :class:`AITimeoutError` — call exceeded ``self._timeout``
            or the SDK raised a timeout.

        Does **not** retry on
        :class:`AIRequestError` (4xx-style) or
        :class:`AIConfigurationError` (programmer error) — those
        will keep failing on every retry.
        """
        return Retrying(
            stop=stop_after_attempt(self._max_retries + 1),
            wait=wait_exponential_jitter(initial=0.5, max=8.0),
            retry=retry_if_exception_type(_RETRYABLE_DOMAIN_ERRORS),
            reraise=True,
        )

    def _call_with_retry(self, fn: Any) -> Any:
        """Call ``fn`` under the retry policy.

        ``fn`` is expected to raise a domain
        :class:`AIProviderError` subclass on failure (the
        :meth:`chat` wrapper translates SDK errors before
        calling this). Tenacity will retry on the transient
        subset (``AIRateLimitError``, ``AIResponseError``,
        ``AITimeoutError``) and re-raise the rest
        (``AIRequestError``, ``AIConfigurationError``) unchanged.
        """
        for attempt in self._retrying():
            with attempt:
                return fn()

    # ------------------------------------------------------------------
    # Error translation
    # ------------------------------------------------------------------

    def _translate_sdk_error(self, exc: BaseException) -> AIProviderError:
        """Map any SDK exception to a domain ``AIProviderError`` subclass."""
        # Lazy import — the SDK is not a hard dependency of the
        # service / domain layers.
        from google.genai import errors as genai_errors

        # 429 — rate limited
        if isinstance(exc, genai_errors.ClientError):
            code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
            if code == 429:
                return AIRateLimitError(str(exc), provider=self.name)
            if isinstance(code, int) and 400 <= code < 500:
                return AIRequestError(str(exc), provider=self.name)
            if isinstance(code, int) and code >= 500:
                return AIResponseError(str(exc), provider=self.name)
            return AIRequestError(str(exc), provider=self.name)

        if isinstance(exc, genai_errors.ServerError):
            return AIResponseError(str(exc), provider=self.name)

        if isinstance(exc, (TimeoutError, genai_errors.APIError)):
            if isinstance(exc, TimeoutError) or "timeout" in str(exc).lower():
                return AITimeoutError(str(exc), provider=self.name)
            return AIResponseError(str(exc), provider=self.name)

        if isinstance(exc, AIProviderError):
            return exc

        return AIResponseError(str(exc), provider=self.name)


# ---------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------

#: Domain errors that represent transient provider failures. The
#: retry policy will re-run the call on these. ``AIRequestError``
#: (4xx-style) is **not** in this set — it indicates a programmer
#: error and should not be retried.
_RETRYABLE_DOMAIN_ERRORS: tuple[type[BaseException], ...] = (
    AIRateLimitError,
    AIResponseError,
    AITimeoutError,
)


__all__ = ["GeminiProvider"]
