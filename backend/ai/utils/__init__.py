"""
AI utility helpers.

Re-exports the small building blocks the provider and service layers
compose. Kept stdlib-only where possible; the rest of the AI package
must not import from ``backend.ai.providers`` or
``backend.ai.services`` to avoid cycles.
"""
from backend.ai.utils.latency import LatencyTimer
from backend.ai.utils.token_estimator import (
    DEFAULT_CHARS_PER_TOKEN,
    estimate_messages_tokens,
    estimate_tokens,
)

__all__ = [
    "LatencyTimer",
    "DEFAULT_CHARS_PER_TOKEN",
    "estimate_messages_tokens",
    "estimate_tokens",
]
