"""
Tests for the AI domain models.

``ChatMessage``, ``ChatRequest``, ``ChatResponse``, and
``ChatRole`` are the lingua franca of the AI layer — every
service, provider, and (future) route depends on their
contract. These tests pin down the validation rules and the
field defaults.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.ai.models.chat import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatRole,
)


# ---------------------------------------------------------------------
# ChatRole
# ---------------------------------------------------------------------


class TestChatRole:
    def test_role_values(self):
        assert ChatRole.SYSTEM.value == "system"
        assert ChatRole.USER.value == "user"
        assert ChatRole.ASSISTANT.value == "assistant"
        assert ChatRole.TOOL.value == "tool"

    def test_role_is_string(self):
        """``ChatRole`` subclasses ``str`` so it serialises naturally."""
        assert ChatRole.USER == "user"


# ---------------------------------------------------------------------
# ChatMessage
# ---------------------------------------------------------------------


class TestChatMessage:
    def test_minimal(self):
        m = ChatMessage(role=ChatRole.USER, content="hi")
        assert m.role == ChatRole.USER
        assert m.content == "hi"

    def test_empty_content_rejected(self):
        with pytest.raises(ValidationError):
            ChatMessage(role=ChatRole.USER, content="")

    def test_forbidden_extras(self):
        with pytest.raises(ValidationError):
            ChatMessage(role=ChatRole.USER, content="x", bogus="y")

    def test_frozen(self):
        m = ChatMessage(role=ChatRole.USER, content="hi")
        with pytest.raises(Exception):
            m.content = "no"  # type: ignore[misc]


# ---------------------------------------------------------------------
# ChatRequest
# ---------------------------------------------------------------------


class TestChatRequest:
    def test_defaults(self):
        r = ChatRequest(
            messages=[ChatMessage(role=ChatRole.USER, content="hi")]
        )
        assert r.system_prompt is None
        assert r.temperature == 0.2
        assert r.max_output_tokens == 1024
        assert r.metadata == {}

    def test_empty_messages_rejected(self):
        with pytest.raises(ValidationError):
            ChatRequest(messages=[])

    def test_temperature_bounds(self):
        with pytest.raises(ValidationError):
            ChatRequest(
                messages=[ChatMessage(role=ChatRole.USER, content="hi")],
                temperature=-0.1,
            )
        with pytest.raises(ValidationError):
            ChatRequest(
                messages=[ChatMessage(role=ChatRole.USER, content="hi")],
                temperature=2.5,
            )

    def test_max_output_tokens_bounds(self):
        with pytest.raises(ValidationError):
            ChatRequest(
                messages=[ChatMessage(role=ChatRole.USER, content="hi")],
                max_output_tokens=0,
            )
        with pytest.raises(ValidationError):
            ChatRequest(
                messages=[ChatMessage(role=ChatRole.USER, content="hi")],
                max_output_tokens=10_000,
            )

    def test_metadata_is_isolated_per_instance(self):
        a = ChatRequest(
            messages=[ChatMessage(role=ChatRole.USER, content="x")]
        )
        b = ChatRequest(
            messages=[ChatMessage(role=ChatRole.USER, content="x")]
        )
        a.metadata["k"] = "v"
        assert b.metadata == {}


# ---------------------------------------------------------------------
# ChatResponse
# ---------------------------------------------------------------------


class TestChatResponse:
    def test_minimal(self):
        r = ChatResponse(
            provider="gemini",
            model="m",
            content="hi",
            latency_ms=10,
        )
        assert r.provider == "gemini"
        assert r.finish_reason is None
        assert r.prompt_tokens is None
        assert r.completion_tokens is None
        assert r.total_tokens is None
        assert r.metadata == {}

    def test_full(self):
        r = ChatResponse(
            provider="gemini",
            model="gemini-2.0-flash",
            content="answer",
            finish_reason="STOP",
            prompt_tokens=5,
            completion_tokens=3,
            total_tokens=8,
            latency_ms=42,
            metadata={"trace_id": "x"},
        )
        assert r.finish_reason == "STOP"
        assert r.prompt_tokens == 5
        assert r.completion_tokens == 3
        assert r.total_tokens == 8
        assert r.metadata == {"trace_id": "x"}
