"""
NVIDIA NIM provider — uses the OpenAI-compatible NIM inference API.

Endpoint: https://integrate.api.nvidia.com/v1
Compatible with any model on build.nvidia.com (llama, mistral, etc.)
Uses the openai SDK in compatibility mode.
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

_NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"

_RETRYABLE_ERRORS: tuple[type[BaseException], ...] = (
    AIRateLimitError,
    AIResponseError,
    AITimeoutError,
)


class NvidiaProvider(AIProvider):
    """AIProvider implementation for NVIDIA NIM (OpenAI-compatible API)."""

    name: str = "nvidia"
    default_model: str = "meta/llama-3.1-8b-instruct"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout: float,
        max_retries: int,
        logger: logging.Logger | None = None,
        client_factory: Any | None = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            model=model,
            timeout=timeout,
            max_retries=max_retries,
            logger=logger,
        )
        self._client: Any | None = None
        self._client_factory = client_factory

    def chat(self, request: "ChatRequest") -> "ChatResponse":
        self._log_call_start(request)
        timer = self._start_timer()

        messages = self._build_messages(request)
        client = self._get_client()

        def _call_once() -> Any:
            try:
                return client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=float(request.temperature),
                    max_tokens=int(request.max_output_tokens),
                    timeout=self._timeout,
                )
            except AIProviderError:
                raise
            except Exception as exc:
                raise self._translate_error(exc) from exc

        try:
            sdk_response = self._call_with_retry(_call_once)
        except AIProviderError as exc:
            self._log_call_failure(timer.elapsed_ms(), exc)
            raise

        latency = timer.elapsed_ms()
        response = self._build_response(sdk_response)
        self._log_call_success(
            latency,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
        )
        return response

    def count_tokens(self, text: str) -> int:
        return estimate_tokens(text)

    def _build_messages(self, request: "ChatRequest") -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if request.system_prompt:
            # Merge system prompt into the first user message for models
            # that don't support system role (e.g. llama-guard variants)
            first_content = f"{request.system_prompt}\n\n"
            for msg in request.messages:
                role = getattr(msg.role, "value", str(msg.role))
                role = "assistant" if role == "assistant" else "user"
                content = msg.content
                if role == "user" and first_content:
                    content = first_content + content
                    first_content = ""
                messages.append({"role": role, "content": content})
        else:
            for msg in request.messages:
                role = getattr(msg.role, "value", str(msg.role))
                role = "assistant" if role == "assistant" else "user"
                messages.append({"role": role, "content": msg.content})
        return messages

    def _build_response(self, sdk_response: Any) -> "ChatResponse":
        from backend.ai.models.chat import ChatResponse

        choice = sdk_response.choices[0] if sdk_response.choices else None
        content = ""
        finish_reason = None
        if choice:
            content = getattr(choice.message, "content", "") or ""
            finish_reason = getattr(choice, "finish_reason", None)

        usage = getattr(sdk_response, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", None)
        completion_tokens = getattr(usage, "completion_tokens", None)
        total_tokens = getattr(usage, "total_tokens", None)

        return ChatResponse(
            provider=self.name,
            model=self.model,
            content=content,
            finish_reason=str(finish_reason) if finish_reason else None,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=0,
            metadata={"provider": self.name, "model": self.model},
        )

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise AIConfigurationError(
                "openai package is not installed. Run `pip install openai`."
            ) from exc
        if self._client_factory is not None:
            self._client = self._client_factory(
                api_key=self._api_key, base_url=_NIM_BASE_URL
            )
        else:
            self._client = OpenAI(api_key=self._api_key, base_url=_NIM_BASE_URL)
        return self._client

    def _retrying(self) -> Retrying:
        return Retrying(
            stop=stop_after_attempt(self._max_retries + 1),
            wait=wait_exponential_jitter(initial=0.5, max=8.0),
            retry=retry_if_exception_type(_RETRYABLE_ERRORS),
            reraise=True,
        )

    def _call_with_retry(self, fn: Any) -> Any:
        for attempt in self._retrying():
            with attempt:
                return fn()

    def _translate_error(self, exc: BaseException) -> AIProviderError:
        msg = str(exc)
        try:
            from openai import RateLimitError, APITimeoutError, APIStatusError
            if isinstance(exc, RateLimitError):
                return AIRateLimitError(msg, provider=self.name)
            if isinstance(exc, APITimeoutError):
                return AITimeoutError(msg, provider=self.name)
            if isinstance(exc, APIStatusError):
                if exc.status_code >= 500:
                    return AIResponseError(msg, provider=self.name)
                return AIRequestError(msg, provider=self.name)
        except ImportError:
            pass
        if "timeout" in msg.lower():
            return AITimeoutError(msg, provider=self.name)
        if "429" in msg or "rate" in msg.lower():
            return AIRateLimitError(msg, provider=self.name)
        return AIResponseError(msg, provider=self.name)


__all__ = ["NvidiaProvider"]
