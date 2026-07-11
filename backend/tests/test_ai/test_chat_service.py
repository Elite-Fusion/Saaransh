"""
ChatService tests.

The service is a thin orchestrator over :class:`AIProvider` and
:class:`PromptService`. We mock the provider (a real Gemini call
must not happen in tests) and use a tmp prompts directory.
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from backend.ai.models.chat import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatRole,
)
from backend.ai.providers.base import AIProvider
from backend.ai.providers.errors import (
    AIProviderError,
    AIRateLimitError,
)
from backend.ai.services.chat_service import ChatService
from backend.ai.services.prompt_service import PromptService


# ---------------------------------------------------------------------
# Provider stub
# ---------------------------------------------------------------------


def _fake_response(
    *, content: str = "hi", provider: str = "gemini", model: str = "m"
) -> ChatResponse:
    return ChatResponse(
        provider=provider,
        model=model,
        content=content,
        finish_reason="STOP",
        prompt_tokens=10,
        completion_tokens=2,
        total_tokens=12,
        latency_ms=5,
        metadata={},
    )


class _StubProvider(AIProvider):
    """Test double that records every chat() invocation."""

    def __init__(self, *, response=None, exc=None, **kwargs):
        super().__init__(api_key="k", model="m", timeout=1, max_retries=0)
        self._response = response or _fake_response()
        self._exc = exc
        self.calls: list[ChatRequest] = []

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.calls.append(request)
        if self._exc is not None:
            raise self._exc
        return self._response

    def count_tokens(self, text: str) -> int:  # pragma: no cover
        return len(text) // 4


# ---------------------------------------------------------------------
# chat(request)
# ---------------------------------------------------------------------


class TestChatServiceChat:
    def test_chat_delegates_to_provider(self):
        provider = _StubProvider(response=_fake_response(content="hello"))
        service = ChatService(provider=provider, prompt_service=PromptService())
        req = ChatRequest(
            messages=[ChatMessage(role=ChatRole.USER, content="hi")],
        )
        out = service.chat(req)
        assert out.content == "hello"
        assert provider.calls == [req]

    def test_chat_logs_start_and_success(self, caplog):
        provider = _StubProvider()
        service = ChatService(
            provider=provider,
            prompt_service=PromptService(),
            logger=logging.getLogger("test"),
        )
        req = ChatRequest(
            messages=[ChatMessage(role=ChatRole.USER, content="hi")],
        )
        with caplog.at_level(logging.INFO, logger="test"):
            service.chat(req)
        msgs = [r.message for r in caplog.records]
        assert any("chat_service_call_start" in m for m in msgs)
        assert any("chat_service_call_success" in m for m in msgs)

    def test_chat_propagates_provider_exception(self):
        exc = AIRateLimitError("throttled", provider="gemini")
        provider = _StubProvider(exc=exc)
        service = ChatService(provider=provider, prompt_service=PromptService())
        req = ChatRequest(
            messages=[ChatMessage(role=ChatRole.USER, content="hi")],
        )
        with pytest.raises(AIProviderError) as ei:
            service.chat(req)
        assert ei.value is exc

    def test_introspection(self):
        provider = _StubProvider()
        prompts = PromptService()
        service = ChatService(provider=provider, prompt_service=prompts)
        assert service.provider is provider
        assert service.prompt_service is prompts


# ---------------------------------------------------------------------
# chat_with_prompt(name, user_message, **vars)
# ---------------------------------------------------------------------


class TestChatServiceChatWithPrompt:
    def test_renders_prompt_and_calls_provider(self, tmp_prompts_dir):
        provider = _StubProvider(response=_fake_response(content="rendered!"))
        prompts = PromptService(prompts_dir=tmp_prompts_dir)
        service = ChatService(provider=provider, prompt_service=prompts)
        out = service.chat_with_prompt(
            "hello",
            "What is the count?",
            officer_name="Officer",
            weekday="Monday",
        )
        assert out.content == "rendered!"
        # The provider received a request with the rendered system prompt
        # and a single user message.
        sent = provider.calls[0]
        assert "Hello Officer! Today is Monday." in (sent.system_prompt or "")
        assert len(sent.messages) == 1
        assert sent.messages[0].role == ChatRole.USER
        assert sent.messages[0].content == "What is the count?"

    def test_missing_prompt_raises(self, tmp_prompts_dir):
        provider = _StubProvider()
        prompts = PromptService(prompts_dir=tmp_prompts_dir)
        service = ChatService(provider=provider, prompt_service=prompts)
        from backend.ai.providers.errors import PromptNotFoundError

        with pytest.raises(PromptNotFoundError):
            service.chat_with_prompt(
                "does_not_exist", "any user message", foo="bar"
            )

    def test_temperature_override(self, tmp_prompts_dir):
        provider = _StubProvider()
        prompts = PromptService(prompts_dir=tmp_prompts_dir)
        service = ChatService(provider=provider, prompt_service=prompts)
        service.chat_with_prompt(
            "hello", "msg", temperature=0.9, officer_name="X", weekday="Y"
        )
        sent = provider.calls[0]
        assert sent.temperature == 0.9

    def test_max_output_tokens_override(self, tmp_prompts_dir):
        provider = _StubProvider()
        prompts = PromptService(prompts_dir=tmp_prompts_dir)
        service = ChatService(provider=provider, prompt_service=prompts)
        service.chat_with_prompt(
            "hello", "msg", max_output_tokens=256, officer_name="X", weekday="Y"
        )
        sent = provider.calls[0]
        assert sent.max_output_tokens == 256

    def test_metadata_is_propagated(self, tmp_prompts_dir):
        provider = _StubProvider()
        prompts = PromptService(prompts_dir=tmp_prompts_dir)
        service = ChatService(provider=provider, prompt_service=prompts)
        service.chat_with_prompt(
            "hello",
            "msg",
            officer_name="X",
            weekday="Y",
            metadata={"user_id": "officer-1"},
        )
        sent = provider.calls[0]
        assert sent.metadata == {"user_id": "officer-1"}
