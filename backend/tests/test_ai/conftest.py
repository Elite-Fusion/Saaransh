"""
Shared fixtures for the AI test suite.

The tests in this package never make a real network call to
Gemini. The :class:`GeminiProvider` accepts a
``client_factory`` hook precisely so we can build a mock
client in-process.

Phase 6 adds helpers for stubbing :class:`ChatService`,
:class:`IntentService`, :class:`SQLGenerationService`, and
:class:`SQLValidationService` — the four collaborators the
:class:`InvestigationService` composes. The test suite can mix
and match them: real ``SQLValidationService`` (it is pure Python)
plus a stub ``ChatService`` (it would otherwise hit Gemini).
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

# Mirror the parent conftest's path setup so we are robust if
# pytest ever collects this package without the parent conftest.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------
# Mock SDK response builders
# ---------------------------------------------------------------------


def make_sdk_response(
    *,
    text: str = "Hello, officer.",
    prompt_tokens: int | None = 12,
    completion_tokens: int | None = 8,
    total_tokens: int | None = 20,
    finish_reason: str = "STOP",
) -> SimpleNamespace:
    """Return a SimpleNamespace that mimics ``GenerateContentResponse``.

    The Gemini provider's response extractors use ``getattr``,
    so we only need to provide the fields the provider reads:
    ``text``, ``candidates[0].finish_reason``,
    ``usage_metadata``, and (fallback) ``candidates[0].content.parts``.
    """
    usage = (
        SimpleNamespace(
            prompt_token_count=prompt_tokens,
            candidates_token_count=completion_tokens,
            total_token_count=total_tokens,
        )
        if prompt_tokens is not None
        or completion_tokens is not None
        or total_tokens is not None
        else None
    )
    return SimpleNamespace(
        text=text,
        candidates=[
            SimpleNamespace(
                finish_reason=SimpleNamespace(name=finish_reason)
                if finish_reason
                else None,
                content=SimpleNamespace(
                    parts=[SimpleNamespace(text=text)],
                ),
            )
        ],
        usage_metadata=usage,
    )


def make_mock_client(*, responses: list | None = None) -> MagicMock:
    """Return a mock that mimics ``genai.Client``.

    Each call to ``client.models.generate_content(...)`` returns
    the next response in ``responses`` (default: a single canned
    response). The first call to ``client.models.count_tokens``
    returns a SimpleNamespace with ``total_tokens=42``.
    """
    client = MagicMock(name="genai.Client")
    if responses is None:
        responses = [make_sdk_response()]
    gen = iter(responses)
    client.models.generate_content.side_effect = lambda **_: next(gen)
    client.models.count_tokens.return_value = SimpleNamespace(total_tokens=42)
    return client


def make_client_factory(client: MagicMock):
    """Return a ``client_factory`` callable suitable for the provider."""
    return MagicMock(return_value=client)


# ---------------------------------------------------------------------
# Reusable fixtures
# ---------------------------------------------------------------------


@pytest.fixture
def sdk_response():
    """Default canned SDK response."""
    return make_sdk_response()


@pytest.fixture
def mock_client(sdk_response):
    """A mock genai client that returns a single canned response."""
    return make_mock_client(responses=[sdk_response])


@pytest.fixture
def client_factory(mock_client):
    """A ``client_factory`` that yields ``mock_client``."""
    return make_client_factory(mock_client)


@pytest.fixture
def tmp_prompts_dir(tmp_path) -> Path:
    """A clean prompts directory with one sample file in it."""
    p = tmp_path / "prompts"
    p.mkdir()
    (p / "hello.md").write_text(
        "Hello {officer_name}! Today is {weekday}.",
        encoding="utf-8",
    )
    (p / "no_vars.md").write_text("Static prompt, no vars.", encoding="utf-8")
    return p


# ---------------------------------------------------------------------
# Phase 6 — ChatService stub for the investigation engine
# ---------------------------------------------------------------------


def make_stub_chat_service(
    *,
    chat_with_prompt_response: Any | None = None,
    chat_with_prompt_exc: Exception | None = None,
    chat_response: Any | None = None,
    chat_exc: Exception | None = None,
) -> MagicMock:
    """Return a MagicMock that mimics :class:`ChatService`.

    Both ``chat()`` and ``chat_with_prompt()`` can be configured to
    raise an exception or return a canned response. The ``return_value``
    on each method is honoured; ``side_effect`` is only attached when an
    exception is supplied so individual tests can ``mock.return_value =
    ...`` to swap the response in place.

    Args:
        chat_with_prompt_response: The value returned by
            ``chat_with_prompt`` (typically a :class:`ChatResponse`
            with ``content`` set to a JSON string).
        chat_with_prompt_exc: An exception for ``chat_with_prompt``
            to raise.
        chat_response: The value returned by ``chat``.
        chat_exc: An exception for ``chat`` to raise.
    """
    stub = MagicMock(name="ChatService")
    stub.chat_with_prompt.return_value = chat_with_prompt_response
    stub.chat.return_value = chat_response
    if chat_with_prompt_exc is not None:
        stub.chat_with_prompt.side_effect = chat_with_prompt_exc
    if chat_exc is not None:
        stub.chat.side_effect = chat_exc
    return stub


def make_chat_response(content: str = "{}", **kwargs: Any) -> SimpleNamespace:
    """Build a minimal ChatResponse-like object with just ``content``."""
    from backend.ai.models.chat import ChatResponse

    return ChatResponse(
        provider=kwargs.get("provider", "gemini"),
        model=kwargs.get("model", "gemini-2.0-flash"),
        content=content,
        finish_reason=kwargs.get("finish_reason", "STOP"),
        prompt_tokens=kwargs.get("prompt_tokens", 1),
        completion_tokens=kwargs.get("completion_tokens", 1),
        total_tokens=kwargs.get("total_tokens", 2),
        latency_ms=kwargs.get("latency_ms", 1),
        metadata=kwargs.get("metadata", {}),
    )


@pytest.fixture
def stub_chat_service():
    """A callable factory for :func:`make_stub_chat_service`."""
    return make_stub_chat_service


@pytest.fixture
def chat_response_factory():
    """A callable factory for :func:`make_chat_response`."""
    return make_chat_response


# ---------------------------------------------------------------------
# Phase 6 — PromptService fixture with all four Phase 6 prompts
# ---------------------------------------------------------------------


@pytest.fixture
def tmp_prompts_dir_with_all(tmp_path) -> Path:
    """A prompts dir that contains every prompt the Phase 6 services
    render. The bodies are small but valid; tests can override
    individual files at runtime."""
    p = tmp_path / "prompts"
    p.mkdir()
    (p / "intent_prompt.md").write_text(
        "INTENT_PROMPT SCHEMA_SUMMARY={schema}",
        encoding="utf-8",
    )
    (p / "sql_prompt.md").write_text(
        "SQL_PROMPT SCHEMA_SUMMARY={SCHEMA_SUMMARY} QUESTION={QUESTION}",
        encoding="utf-8",
    )
    (p / "explanation_prompt.md").write_text(
        "EXPLANATION_PROMPT QUESTION={QUESTION} SQL={SQL} "
        "ROWS_JSON={ROWS_JSON} ROW_COUNT={ROW_COUNT} FILTERS={FILTERS}",
        encoding="utf-8",
    )
    (p / "investigation_prompt.md").write_text(
        "INVESTIGATION_PROMPT", encoding="utf-8"
    )
    (p / "system_prompt.md").write_text("SYSTEM", encoding="utf-8")
    return p
