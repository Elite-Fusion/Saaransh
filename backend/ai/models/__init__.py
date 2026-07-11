"""
AI domain models.

Re-exports the chat message / request / response models. Other domain
models (embedding requests, similarity results, voice transcripts) will
land here in later phases.
"""
from backend.ai.models.chat import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatRole,
)

__all__ = [
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "ChatRole",
]
