"""
Provider factory — the **single** place that knows how to build a
concrete :class:`~backend.ai.providers.base.AIProvider` from the
runtime configuration.

Adding a new provider means:

  1. Implementing a new subclass of
     :class:`~backend.ai.providers.base.AIProvider` in
     :mod:`backend.ai.providers`.
  2. Adding a branch to :func:`get_provider` below.
  3. Adding the corresponding ``<provider>_api_key`` /
     ``<provider>_model`` entries to
     :class:`backend.config.settings.Settings`.

Nothing else changes — services, routes, and the rest of the
codebase keep talking to :class:`AIProvider`.
"""
from __future__ import annotations

import functools
import logging
from typing import TYPE_CHECKING

from backend.ai.providers.base import AIProvider
from backend.ai.providers.errors import (
    AIConfigurationError,
    UnsupportedProviderError,
)
from backend.ai.providers.gemini import GeminiProvider

if TYPE_CHECKING:
    from backend.config.settings import Settings


_LOGGER = logging.getLogger("backend.ai.providers.factory")


@functools.lru_cache(maxsize=1)
def get_provider() -> AIProvider:
    """Return the singleton :class:`AIProvider` for the configured backend.

    The provider is selected from
    :attr:`backend.config.settings.Settings.ai_provider`. The
    ``lru_cache`` wrapper means we build it exactly once per
    process — ``Settings`` is read on the first call and not
    re-read afterwards.

    Returns:
        A fully-configured :class:`AIProvider`.

    Raises:
        UnsupportedProviderError: ``settings.ai_provider`` is not
            one of the providers implemented in Phase 5 (currently
            only ``"gemini"``).
        AIConfigurationError: The required credentials for the
            selected provider are missing (e.g. an empty
            ``GEMINI_API_KEY``).
    """
    # Imported lazily so importing this module does not require
    # ``Settings`` to be valid (relevant for unit tests that build
    # the AI layer without a full app context).
    from backend.config.settings import get_settings

    settings = get_settings()
    return _build_provider(settings)


def _build_provider(settings: "Settings") -> AIProvider:
    """Dispatch to the right concrete provider.

    Args:
        settings: The runtime settings. Must already be validated
            by :class:`backend.config.settings.Settings` —
            this function assumes ``ai_provider`` is one of the
            known string literals.

    Returns:
        A concrete :class:`AIProvider`.

    Raises:
        UnsupportedProviderError: ``settings.ai_provider`` is
            unknown.
        AIConfigurationError: A required credential is empty.
    """
    name = (settings.ai_provider or "").strip().lower()
    if name == "gemini":
        return _build_gemini(settings)
    # The literal is the only branch today. Future phases add
    # ``"claude"``, ``"openai"``, ``"groq"``, ``"openrouter"``.
    raise UnsupportedProviderError(
        f"AI provider '{name}' is not supported. "
        f"Implemented providers: 'gemini'.",
        provider=name or "<unset>",
    )


def _build_gemini(settings: "Settings") -> GeminiProvider:
    """Build the Gemini provider from validated settings."""
    if not settings.gemini_api_key:
        raise AIConfigurationError(
            "GEMINI_API_KEY is empty. Set the environment variable "
            "before starting the backend.",
            provider="gemini",
        )
    return GeminiProvider(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        timeout=settings.ai_request_timeout_seconds,
        max_retries=settings.ai_max_retries,
        logger=_LOGGER,
    )


def reset_provider_cache() -> None:
    """Drop the cached provider.

    Test-only helper: lets a test exercise multiple ``ai_provider``
    values without leaking state across cases. Not for production
    callers — the singleton is part of the design.
    """
    get_provider.cache_clear()


__all__ = ["get_provider", "reset_provider_cache"]
