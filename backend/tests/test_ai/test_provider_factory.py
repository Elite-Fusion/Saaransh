"""
ProviderFactory tests.

Covers the three behaviours we depend on:

  * ``get_provider()`` returns a :class:`GeminiProvider` when
    ``ai_provider == "gemini"``.
  * Unknown values raise :class:`UnsupportedProviderError`.
  * Empty ``gemini_api_key`` raises
    :class:`AIConfigurationError`.

The factory caches the singleton; tests use
``reset_provider_cache`` to start from a clean slate.
"""
from __future__ import annotations

import pytest

from backend.ai.providers.errors import (
    AIConfigurationError,
    UnsupportedProviderError,
)
from backend.ai.providers.factory import get_provider, reset_provider_cache


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _set_provider(name: str, *, api_key: str = "test-key") -> None:
    """Mutate the cached Settings so the factory picks up the value.

    The conftest already initialised Settings once. Mutating the
    cached instance is fine for tests — pydantic-settings does
    not re-read the env on attribute access.
    """
    from backend.config import settings

    settings.ai_provider = name
    settings.gemini_api_key = api_key
    settings.gemini_model = "gemini-2.0-flash"
    settings.ai_request_timeout_seconds = 30.0
    settings.ai_max_retries = 3
    settings.ai_prompts_dir = ""


@pytest.fixture(autouse=True)
def _isolate():
    """Reset the cached provider and put Settings back to a
    safe default at the end of every test."""
    reset_provider_cache()
    yield
    reset_provider_cache()
    _set_provider("gemini", api_key="test-key")


# ---------------------------------------------------------------------
# Behaviour
# ---------------------------------------------------------------------


class TestGetProvider:
    def test_returns_gemini_provider_by_default(self):
        _set_provider("gemini", api_key="test-key")
        provider = get_provider()
        assert provider.name == "gemini"

    def test_provider_is_singleton(self):
        _set_provider("gemini", api_key="test-key")
        a = get_provider()
        b = get_provider()
        assert a is b

    def test_provider_carries_configured_model(self):
        _set_provider("gemini", api_key="test-key")
        from backend.config import settings

        settings.gemini_model = "gemini-1.5-pro"
        reset_provider_cache()
        provider = get_provider()
        assert provider.model == "gemini-1.5-pro"

    def test_unknown_provider_raises(self):
        _set_provider("claude")  # not supported in Phase 5
        with pytest.raises(UnsupportedProviderError) as exc:
            get_provider()
        assert "claude" in str(exc.value).lower()

    def test_empty_gemini_key_raises(self):
        _set_provider("gemini", api_key="")
        with pytest.raises(AIConfigurationError) as exc:
            get_provider()
        assert "GEMINI_API_KEY" in str(exc.value)


# ---------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------


class TestResetProviderCache:
    def test_reset_clears_singleton(self):
        _set_provider("gemini", api_key="k1")
        a = get_provider()
        reset_provider_cache()
        # Mutate the underlying settings — a fresh provider should
        # observe the new value.
        _set_provider("gemini", api_key="k2")
        b = get_provider()
        assert a is not b
