"""
Best-effort token estimator.

Used by the provider layer as a *fallback* when the upstream provider
does not expose a count-tokens endpoint. The estimate is approximate
and intentionally conservative — over-estimate is safer than
under-estimate when the goal is to keep the request under the model's
context limit.

The default heuristic is the long-standing "≈ 4 characters per token"
rule of thumb. It is wrong for code, math, and many non-English
scripts; we use it only as a last-resort gate, never as a billing input.
"""
from __future__ import annotations

# Average number of characters per token across the most common
# English-language corpora. Adjust per-locale in a future phase.
DEFAULT_CHARS_PER_TOKEN = 4


def estimate_tokens(text: str, *, chars_per_token: int = DEFAULT_CHARS_PER_TOKEN) -> int:
    """Return an approximate token count for ``text``.

    Args:
        text: The string to measure. Empty strings return ``0``.
        chars_per_token: Override the heuristic. Must be ``>= 1``;
            smaller values produce larger estimates.

    Returns:
        ``ceil(len(text) / chars_per_token)``. Never returns a negative
        number, even for empty input.

    Note:
        This is a heuristic. For accurate counts, call the provider's
        native count-tokens API (e.g. ``client.models.count_tokens(...)``
        on Gemini).
    """
    if not text:
        return 0
    if chars_per_token < 1:
        raise ValueError("chars_per_token must be >= 1")
    # Ceiling division so an 8-character string at 4 cpt → 2 tokens,
    # not 1. This is the conservative side of the heuristic.
    return (len(text) + chars_per_token - 1) // chars_per_token


def estimate_messages_tokens(messages: list, *, chars_per_token: int = DEFAULT_CHARS_PER_TOKEN) -> int:
    """Estimate the total tokens across a list of message objects.

    Each message is expected to expose a ``.content`` attribute (string)
    — matches the :class:`backend.ai.models.chat.ChatMessage` shape. A
    flat sum of per-message estimates; we do not add an overhead for
    role markers because the heuristic is already approximate.
    """
    if not messages:
        return 0
    total = 0
    for msg in messages:
        content = getattr(msg, "content", "")
        if isinstance(content, str):
            total += estimate_tokens(content, chars_per_token=chars_per_token)
    return total
