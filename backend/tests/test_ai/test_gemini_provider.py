"""
GeminiProvider tests — the only concrete provider in Phase 5.

Every test mocks the SDK so no real network call is made.
We exercise:

  * Construction & validation
  * Lazy client building
  * ``chat()`` payload construction and response mapping
  * Error translation to the domain hierarchy
  * Retry policy on transient failures
  * No-retry behaviour on programmer errors
  * ``count_tokens()`` (SDK path + fallback to estimator)
  * The ``client_factory`` test hook
"""
from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.ai.models.chat import (
    ChatMessage,
    ChatRequest,
    ChatRole,
)
from backend.ai.providers.errors import (
    AIConfigurationError,
    AIProviderError,
    AIRateLimitError,
    AIRequestError,
    AIResponseError,
    AITimeoutError,
)
from backend.ai.providers.gemini import GeminiProvider
from backend.ai.utils.token_estimator import estimate_tokens


# ---------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------


class TestGeminiProviderConstruction:
    def test_minimal_construction(self):
        provider = GeminiProvider(
            api_key="k", model="m", timeout=1.0, max_retries=0
        )
        assert provider.name == "gemini"
        assert provider.model == "m"
        assert provider._client is None  # lazy

    def test_empty_api_key_rejected(self):
        with pytest.raises(ValueError):
            GeminiProvider(
                api_key="", model="m", timeout=1.0, max_retries=0
            )

    def test_empty_model_rejected(self):
        with pytest.raises(ValueError):
            GeminiProvider(
                api_key="k", model="", timeout=1.0, max_retries=0
            )

    def test_zero_timeout_rejected(self):
        with pytest.raises(ValueError):
            GeminiProvider(
                api_key="k", model="m", timeout=0, max_retries=0
            )

    def test_negative_retries_rejected(self):
        with pytest.raises(ValueError):
            GeminiProvider(
                api_key="k", model="m", timeout=1.0, max_retries=-1
            )

    def test_repr_is_diagnostic(self):
        provider = GeminiProvider(
            api_key="k", model="m", timeout=1.0, max_retries=0
        )
        r = repr(provider)
        assert "GeminiProvider" in r
        assert "gemini" in r
        assert "m" in r


# ---------------------------------------------------------------------
# Lazy client
# ---------------------------------------------------------------------


class TestClientBuilding:
    def test_client_built_lazily(self, client_factory, mock_client):
        provider = GeminiProvider(
            api_key="k",
            model="m",
            timeout=1.0,
            max_retries=0,
            client_factory=client_factory,
        )
        assert provider._client is None
        # Trigger lazy build by calling count_tokens
        provider.count_tokens("hello")
        client_factory.assert_called_once_with(api_key="k")
        assert provider._client is mock_client

    def test_missing_sdk_raises_configuration_error(self):
        """When the google-genai SDK is not importable, ``_get_client``
        surfaces an :class:`AIConfigurationError`. The public
        ``count_tokens`` swallows that and falls back to the
        estimator — this test pins down the *underlying* contract."""
        provider = GeminiProvider(
            api_key="k", model="m", timeout=1.0, max_retries=0
        )
        with patch.dict(
            "sys.modules",
            {"google": None, "google.genai": None},
        ):
            with pytest.raises(AIConfigurationError):
                provider._get_client()

    def test_count_tokens_falls_back_when_sdk_missing(self):
        """``count_tokens`` is non-critical: when the SDK is not
        installed, it returns the estimator's number, never an
        exception."""
        provider = GeminiProvider(
            api_key="k", model="m", timeout=1.0, max_retries=0
        )
        with patch.dict(
            "sys.modules",
            {"google": None, "google.genai": None},
        ):
            out = provider.count_tokens("hello world")
        assert out == estimate_tokens("hello world")

    def test_real_client_factory_path(self):
        """When no factory is supplied, the provider builds a real
        ``genai.Client(api_key=...)`` — verify the constructor was
        invoked with the configured key. The actual SDK call is
        exercised in every other test via the ``client_factory``
        hook; this just pins the unwired path."""
        with patch("google.genai.Client") as ClientMock:
            ClientMock.return_value = MagicMock(name="client")
            provider = GeminiProvider(
                api_key="k", model="m", timeout=1.0, max_retries=0
            )
            client = provider._get_client()
            ClientMock.assert_called_once_with(api_key="k")
            assert client is not None
            # Cache hit: second call does not re-invoke the constructor.
            again = provider._get_client()
            assert again is client
            ClientMock.assert_called_once()


# ---------------------------------------------------------------------
# chat() happy path
# ---------------------------------------------------------------------


def _req(text: str = "How many cases in Mysuru?") -> ChatRequest:
    return ChatRequest(
        messages=[ChatMessage(role=ChatRole.USER, content=text)],
        system_prompt="You are Saaransh.",
        temperature=0.2,
        max_output_tokens=512,
        metadata={"trace_id": "abc"},
    )


class TestChat:
    def test_chat_returns_chat_response(self, client_factory, sdk_response):
        provider = GeminiProvider(
            api_key="k", model="m", timeout=1.0, max_retries=0,
            client_factory=client_factory,
        )
        response = provider.chat(_req())
        assert response.provider == "gemini"
        assert response.model == "m"
        assert response.content == "Hello, officer."
        assert response.finish_reason == "STOP"
        assert response.prompt_tokens == 12
        assert response.completion_tokens == 8
        assert response.total_tokens == 20
        assert response.latency_ms >= 0
        assert response.metadata.get("trace_id") == "abc"
        assert response.metadata.get("provider") == "gemini"

    def test_chat_logs_start_and_success(
        self, client_factory, sdk_response, caplog
    ):
        provider = GeminiProvider(
            api_key="k", model="m", timeout=1.0, max_retries=0,
            client_factory=client_factory, logger=logging.getLogger("test"),
        )
        with caplog.at_level(logging.INFO, logger="test"):
            provider.chat(_req())
        msgs = [r.message for r in caplog.records]
        assert any("ai_call_start" in m for m in msgs)
        assert any("ai_call_success" in m for m in msgs)

    def test_chat_does_not_log_prompt(
        self, client_factory, sdk_response, caplog
    ):
        provider = GeminiProvider(
            api_key="k", model="m", timeout=1.0, max_retries=0,
            client_factory=client_factory, logger=logging.getLogger("test"),
        )
        with caplog.at_level(logging.INFO, logger="test"):
            provider.chat(_req("SENSITIVE PROMPT"))
        joined = "\n".join(r.message for r in caplog.records)
        assert "SENSITIVE PROMPT" not in joined

    def test_chat_no_system_prompt(self, client_factory, sdk_response):
        """When ``system_prompt`` is empty, we must not pass
        ``system_instruction`` to the config (the SDK treats it
        as an error)."""
        provider = GeminiProvider(
            api_key="k", model="m", timeout=1.0, max_retries=0,
            client_factory=client_factory,
        )
        request = ChatRequest(
            messages=[ChatMessage(role=ChatRole.USER, content="hi")],
        )
        provider.chat(request)
        # Inspect the call args
        call = client_factory().models.generate_content.call_args
        config = call.kwargs["config"]
        # ``system_instruction`` is set only when truthy.
        # Pydantic may have set it to None — assert it is falsy.
        assert not getattr(config, "system_instruction", None)

    def test_chat_maps_messages_to_content_parts(
        self, client_factory, sdk_response
    ):
        provider = GeminiProvider(
            api_key="k", model="m", timeout=1.0, max_retries=0,
            client_factory=client_factory,
        )
        request = ChatRequest(
            messages=[
                ChatMessage(role=ChatRole.SYSTEM, content="be terse"),
                ChatMessage(role=ChatRole.USER, content="hi"),
                ChatMessage(role=ChatRole.ASSISTANT, content="hello"),
            ],
        )
        provider.chat(request)
        contents = client_factory().models.generate_content.call_args.kwargs[
            "contents"
        ]
        # system is folded into user per the provider's role map;
        # assistant becomes "model".
        roles = [c.role for c in contents]
        assert "model" in roles
        assert all(r in ("user", "model") for r in roles)

    def test_chat_falls_back_to_candidate_text(
        self, client_factory
    ):
        """If the SDK omits ``.text`` (some paths do), we read the
        first candidate's content.parts[0].text."""
        response = SimpleNamespace(
            text="",
            candidates=[
                SimpleNamespace(
                    finish_reason=None,
                    content=SimpleNamespace(
                        parts=[SimpleNamespace(text="from candidates")]
                    ),
                )
            ],
            usage_metadata=None,
        )
        client = MagicMock()
        client.models.generate_content.return_value = response
        provider = GeminiProvider(
            api_key="k", model="m", timeout=1.0, max_retries=0,
            client_factory=MagicMock(return_value=client),
        )
        out = provider.chat(_req())
        assert out.content == "from candidates"

    def test_chat_empty_response_yields_empty_content(self, client_factory):
        response = SimpleNamespace(
            text="", candidates=[], usage_metadata=None
        )
        client = MagicMock()
        client.models.generate_content.return_value = response
        provider = GeminiProvider(
            api_key="k", model="m", timeout=1.0, max_retries=0,
            client_factory=MagicMock(return_value=client),
        )
        out = provider.chat(_req())
        assert out.content == ""
        assert out.finish_reason is None
        assert out.prompt_tokens is None


# ---------------------------------------------------------------------
# Error translation
# ---------------------------------------------------------------------


def _raise(exc):
    """Build a mock client whose ``generate_content`` raises ``exc``."""
    client = MagicMock()
    client.models.generate_content.side_effect = exc
    return client


def _client_error(code: int, body=None) -> "Exception":
    """Build a real ``google.genai.errors.ClientError`` for tests."""
    from google.genai import errors as genai_errors

    return genai_errors.ClientError(code, body or {})


def _server_error(code: int = 503, body=None) -> "Exception":
    """Build a real ``google.genai.errors.ServerError`` for tests."""
    from google.genai import errors as genai_errors

    return genai_errors.ServerError(code, body or {})


def _api_error(message: str = "weird") -> "Exception":
    from google.genai import errors as genai_errors

    return genai_errors.APIError(message, {})


class TestErrorTranslation:
    """A 4xx-style SDK error is *not* retried and surfaces as
    ``AIRequestError`` (or a more specific subclass). 5xx / 429 /
    timeout-style errors are retried by the policy and surface as
    ``AIResponseError`` / ``AIRateLimitError`` / ``AITimeoutError``
    after exhaustion."""

    def test_rate_limit_translates_to_airatelimiterror(self):
        exc = _client_error(429)
        provider = GeminiProvider(
            api_key="k", model="m", timeout=1.0, max_retries=0,
            client_factory=MagicMock(return_value=_raise(exc)),
        )
        with pytest.raises(AIRateLimitError) as ei:
            provider.chat(_req())
        assert ei.value.provider == "gemini"

    def test_4xx_translates_to_airequesterror(self):
        exc = _client_error(400)
        provider = GeminiProvider(
            api_key="k", model="m", timeout=1.0, max_retries=0,
            client_factory=MagicMock(return_value=_raise(exc)),
        )
        with pytest.raises(AIRequestError):
            provider.chat(_req())

    def test_5xx_translates_to_airesponseerror(self):
        exc = _server_error(503)
        provider = GeminiProvider(
            api_key="k", model="m", timeout=1.0, max_retries=0,
            client_factory=MagicMock(return_value=_raise(exc)),
        )
        with pytest.raises(AIResponseError):
            provider.chat(_req())

    def test_timeout_translates_to_aitimeouterror(self):
        provider = GeminiProvider(
            api_key="k", model="m", timeout=1.0, max_retries=0,
            client_factory=MagicMock(return_value=_raise(TimeoutError("slow"))),
        )
        with pytest.raises(AITimeoutError):
            provider.chat(_req())

    def test_unexpected_sdk_error_translates_to_airesponseerror(self):
        exc = _api_error("something weird")
        provider = GeminiProvider(
            api_key="k", model="m", timeout=1.0, max_retries=0,
            client_factory=MagicMock(return_value=_raise(exc)),
        )
        with pytest.raises(AIResponseError):
            provider.chat(_req())

    def test_unknown_exception_translates_to_airesponseerror(self):
        provider = GeminiProvider(
            api_key="k", model="m", timeout=1.0, max_retries=0,
            client_factory=MagicMock(return_value=_raise(ValueError("oops"))),
        )
        with pytest.raises(AIResponseError):
            provider.chat(_req())


# ---------------------------------------------------------------------
# Retry policy
# ---------------------------------------------------------------------


class TestRetryPolicy:
    def test_retries_on_429_until_exhausted(self):
        exc = _client_error(429)
        client = _raise(exc)
        provider = GeminiProvider(
            api_key="k", model="m", timeout=1.0, max_retries=2,
            client_factory=MagicMock(return_value=client),
        )
        with pytest.raises(AIRateLimitError):
            provider.chat(_req())
        # max_retries=2 → 1 + 2 = 3 attempts.
        assert client.models.generate_content.call_count == 3

    def test_retries_on_5xx_until_exhausted(self):
        exc = _server_error(503)
        client = _raise(exc)
        provider = GeminiProvider(
            api_key="k", model="m", timeout=1.0, max_retries=3,
            client_factory=MagicMock(return_value=client),
        )
        with pytest.raises(AIResponseError):
            provider.chat(_req())
        assert client.models.generate_content.call_count == 4

    def test_does_not_retry_on_4xx(self):
        exc = _client_error(400)
        client = _raise(exc)
        provider = GeminiProvider(
            api_key="k", model="m", timeout=1.0, max_retries=5,
            client_factory=MagicMock(return_value=client),
        )
        with pytest.raises(AIRequestError):
            provider.chat(_req())
        assert client.models.generate_content.call_count == 1

    def test_succeeds_after_retry(self, sdk_response):
        exc = _server_error(503)
        # Fail twice, succeed on the third call.
        client = MagicMock()
        client.models.generate_content.side_effect = [exc, exc, sdk_response]
        provider = GeminiProvider(
            api_key="k", model="m", timeout=1.0, max_retries=3,
            client_factory=MagicMock(return_value=client),
        )
        out = provider.chat(_req())
        assert out.content == "Hello, officer."
        assert client.models.generate_content.call_count == 3


# ---------------------------------------------------------------------
# count_tokens
# ---------------------------------------------------------------------


class TestCountTokens:
    def test_empty_text_returns_zero(self, client_factory):
        provider = GeminiProvider(
            api_key="k", model="m", timeout=1.0, max_retries=0,
            client_factory=client_factory,
        )
        assert provider.count_tokens("") == 0

    def test_uses_sdk_when_available(self, client_factory):
        client_factory().models.count_tokens.return_value = SimpleNamespace(
            total_tokens=42
        )
        provider = GeminiProvider(
            api_key="k", model="m", timeout=1.0, max_retries=0,
            client_factory=client_factory,
        )
        assert provider.count_tokens("hello world") == 42

    def test_falls_back_to_estimator_on_sdk_error(
        self, client_factory
    ):
        client_factory().models.count_tokens.side_effect = RuntimeError(
            "boom"
        )
        provider = GeminiProvider(
            api_key="k", model="m", timeout=1.0, max_retries=0,
            client_factory=client_factory,
        )
        out = provider.count_tokens("hello world")
        assert out == estimate_tokens("hello world")

    def test_falls_back_when_sdk_returns_no_tokens(self, client_factory):
        client_factory().models.count_tokens.return_value = SimpleNamespace(
            total_tokens=None
        )
        provider = GeminiProvider(
            api_key="k", model="m", timeout=1.0, max_retries=0,
            client_factory=client_factory,
        )
        out = provider.count_tokens("hello world")
        assert out == estimate_tokens("hello world")
