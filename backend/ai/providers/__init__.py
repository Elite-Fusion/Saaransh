"""
AI provider implementations.

The public surface of this package is the three callables
:class:`AIProvider`, :class:`GeminiProvider`, and
:func:`get_provider`. Services and routes depend on
:class:`AIProvider` only — never on a concrete subclass.

Adding a new provider:

  1. Subclass :class:`AIProvider` in a new module.
  2. Add a branch in
     :func:`backend.ai.providers.factory.get_provider`.
  3. Add the corresponding settings entries.
"""
from __future__ import annotations

from backend.ai.providers.base import AIProvider
from backend.ai.providers.factory import get_provider, reset_provider_cache
from backend.ai.providers.gemini import GeminiProvider

__all__ = [
    "AIProvider",
    "GeminiProvider",
    "get_provider",
    "reset_provider_cache",
]
