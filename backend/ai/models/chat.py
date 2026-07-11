"""
Domain models for the AI layer.

Pydantic v2 models that describe a single chat call. They are
**not** Pydantic-FastAPI response models — they are domain objects
shared between the service layer (which builds them) and the
(future) route layer (which will translate them to JSON).

Why a separate model from the API response shape?

  * ``ChatResponse.latency_ms`` and ``metadata`` are useful to the
    service layer (logging, audit, retry logic) but should not be
    exposed verbatim to a public API client.
  * The future ``/api/v1/ai/*`` routes will wrap ``ChatResponse`` in
    an envelope ``{"data": ..., "meta": {...}}`` — see
    ``backend/ai/docs/ai_api_plan.md``. Keeping the domain model
    small makes that wrapping straightforward.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChatRole(str, Enum):
    """Role of a message in a chat conversation.

    Matches the canonical OpenAI-style roles. Most providers accept
    "system", "user", and "assistant"; some also support "tool".
    """

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ChatMessage(BaseModel):
    """A single message in a chat conversation.

    Plain string content — multimodal content is out of scope for
    Phase 5 (text-only chat). A future phase may extend ``content``
    to a discriminated union (text | image_url | audio).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    role: ChatRole = Field(..., description="Speaker of the message")
    content: str = Field(
        ...,
        min_length=1,
        description="Text content of the message",
    )


class ChatRequest(BaseModel):
    """Inputs to a single chat call.

    Designed to be provider-agnostic. The provider layer translates
    these fields into the SDK's native call shape (Gemini's
    ``GenerateContentConfig`` today; Claude's ``messages.create``
    in a future phase; etc.).
    """

    model_config = ConfigDict(extra="forbid")

    messages: list[ChatMessage] = Field(
        ...,
        min_length=1,
        description=(
            "Conversation history, oldest first. Must contain at "
            "least one message; empty conversations are rejected."
        ),
    )
    system_prompt: str | None = Field(
        default=None,
        description=(
            "Optional system instruction. When present, providers "
            "map it to their native 'system' channel (e.g. "
            "Gemini's ``system_instruction``)."
        ),
    )
    temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="Sampling temperature. 0.0 = deterministic.",
    )
    max_output_tokens: int = Field(
        default=1024,
        ge=1,
        le=8192,
        description="Upper bound on completion length.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Free-form pass-through bag for caller context "
            "(e.g. ``{\"officer_id\": 7, \"case_id\": 12}``). "
            "Echoed on the response and in logs."
        ),
    )


class ChatResponse(BaseModel):
    """Result of a single chat call.

    Includes provider-agnostic metadata (latency, token usage) plus a
    pass-through ``metadata`` bag. The ``content`` field is the model's
    text reply.
    """

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(..., description='Provider name (e.g. "gemini").')
    model: str = Field(..., description="Concrete model id used for the call.")
    content: str = Field(..., description="Model's text reply.")
    finish_reason: str | None = Field(
        default=None,
        description=(
            "Provider-reported stop reason ('stop', 'max_tokens', "
            "'safety', etc.). None when the provider does not report it."
        ),
    )
    prompt_tokens: int | None = Field(
        default=None,
        ge=0,
        description="Input tokens, if the provider reported them.",
    )
    completion_tokens: int | None = Field(
        default=None,
        ge=0,
        description="Output tokens, if the provider reported them.",
    )
    total_tokens: int | None = Field(
        default=None,
        ge=0,
        description="Sum of prompt + completion, if both are known.",
    )
    latency_ms: int = Field(..., ge=0, description="Wall-clock duration of the call.")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Echo of the request metadata, plus provider-specific extras.",
    )
