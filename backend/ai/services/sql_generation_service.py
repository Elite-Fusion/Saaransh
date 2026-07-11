"""
SQLGenerationService — render the SQL prompt, call the LLM, parse the
JSON reply into a :class:`GeneratedSQL`.

The service is the third stage of the investigation pipeline. It
relies on:

  * :file:`backend/ai/prompts/sql_prompt.md` — the system prompt that
    asks the model for a JSON object shaped like
    :class:`~backend.ai.schemas.ai.GeneratedSQL`.
  * :class:`~backend.ai.services.chat_service.ChatService` — the
    thin orchestrator over the LLM provider.
  * :class:`~backend.ai.services.ai_query_service.AIQueryService`
    (or its ``get_schema_summary`` method) — the schema allowlist
    rendered as Markdown for the ``{{SCHEMA_SUMMARY}}`` placeholder.

The service is **provider-agnostic** and **FastAPI-independent**.
The SQL it produces is a string + a parameter dict — no execution
happens here. The validator and the executor are downstream
concerns.

Failure modes:

  * The model returns prose instead of JSON. The service extracts
    the first JSON object from the reply (same logic the intent
    service uses). If nothing parses, the service raises
    :class:`ProviderFailure` with a clear message.
  * The parsed JSON does not match the :class:`GeneratedSQL` schema
    (e.g. missing ``sql``). Same outcome.
  * The model explicitly returns an empty SQL string ("request is
    not a read query"). The service raises
    :class:`UnsafeSQL` so the investigation pipeline can short-circuit.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Mapping

from pydantic import ValidationError

from backend.ai.providers.errors import (
    AIProviderError,
    PromptNotFoundError,
)
from backend.ai.schemas.ai import (
    ALLOWED_SQL_VERBS,
    GeneratedSQL,
)
from backend.ai.services.chat_service import ChatService
from backend.ai.services.exceptions import (
    PromptError,
    ProviderFailure,
    UnsafeSQL,
)

SQL_PROMPT_NAME = "sql_prompt"
_RAW_REPLY_CAP = 4000


class SQLGenerationService:
    """Generate a :class:`GeneratedSQL` from a natural-language question.

    Args:
        chat_service: The :class:`ChatService` the service delegates to.
        schema_summary: A pre-rendered Markdown summary of the
            allowlisted tables. If ``None``, the service builds one
            from :data:`backend.services.schema_registry.SCHEMA_TABLES`
            on first use (cached on the instance).
        logger: Optional :class:`logging.Logger`.
    """

    def __init__(
        self,
        *,
        chat_service: ChatService,
        schema_summary: str | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._chat = chat_service
        self._schema_summary = schema_summary
        self._logger = logger or logging.getLogger(
            "backend.ai.services.sql_generation_service"
        )

    # ------------------------------------------------------------------
    # Public surface
    # ------------------------------------------------------------------

    def generate(
        self,
        question: str,
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> GeneratedSQL:
        """Ask the LLM for a parameterised ``SELECT`` and return it.

        Args:
            question: The officer's natural-language question.
            metadata: Optional metadata dict propagated to the LLM
                call. Useful for request ids, officer ids, etc.

        Returns:
            A populated :class:`GeneratedSQL`. The caller is
            expected to pass it to
            :class:`~backend.ai.services.sql_validation_service.SQLValidationService`
            next.

        Raises:
            UnsafeSQL: The model returned an empty SQL string (e.g.
                the request was not a read query, or the model
                explicitly refused). The route layer maps this to 400.
            PromptError: The SQL prompt file is missing on disk.
            ProviderFailure: The :class:`ChatService` raised, or the
                reply could not be parsed as JSON.
        """
        schema_summary = self._get_schema_summary()
        try:
            response = self._chat.chat_with_prompt(
                SQL_PROMPT_NAME,
                question,
                temperature=0.0,
                max_output_tokens=1024,
                metadata=dict(metadata or {}),
                SCHEMA_SUMMARY=schema_summary,
                QUESTION=question,
            )
        except PromptNotFoundError as exc:
            raise PromptError(SQL_PROMPT_NAME, original=exc) from exc
        except AIProviderError as exc:
            raise ProviderFailure(
                f"LLM call failed: {exc}",
                original=exc,
                provider=getattr(exc, "provider", None),
            ) from exc

        raw = response.content or ""
        return self._parse_reply(raw)

    # ------------------------------------------------------------------
    # Reply parsing
    # ------------------------------------------------------------------

    def _parse_reply(self, raw: str) -> GeneratedSQL:
        """Extract a :class:`GeneratedSQL` from the LLM reply.

        The model is asked to return a JSON object only. Gemini often
        wraps the JSON in ````json ... ```` fences or sprinkles
        Markdown around it. We try:
          1. the raw text;
          2. the first fenced JSON block;
          3. the substring between the first ``{`` and the last ``}``.
        """
        parsed = _extract_json_object(raw)
        if parsed is None:
            self._logger.info(
                "sql_generation_unparseable raw=%r", raw[:200]
            )
            raise ProviderFailure(
                "LLM reply could not be parsed as JSON.",
            )

        try:
            generated = GeneratedSQL.model_validate(parsed)
        except ValidationError as exc:
            raise ProviderFailure(
                f"LLM reply did not match the GeneratedSQL schema: {exc}"
            ) from exc

        if not generated.sql.strip():
            # The model returned the explicit "not a read query" stub
            # documented in sql_prompt.md. The notes field usually
            # carries the reason.
            raise UnsafeSQL(
                generated.notes or "The request is not a read query.",
                sql="",
                category="empty_sql",
            )

        # Normalise the params keys: strip a leading ':' so callers
        # can pass either form to SQLAlchemy.
        generated.params = {
            _strip_colon_prefix(k): v for k, v in (generated.params or {}).items()
        }
        return generated

    # ------------------------------------------------------------------
    # Schema summary
    # ------------------------------------------------------------------

    def _get_schema_summary(self) -> str:
        """Return the cached schema summary, building it on first use."""
        if self._schema_summary is None:
            from backend.services.schema_registry import get_schema_summary

            self._schema_summary = get_schema_summary()
        return self._schema_summary

    @property
    def schema_summary(self) -> str:
        """The schema summary that gets injected into the prompt."""
        return self._get_schema_summary()


# ---------------------------------------------------------------------
# Module-level helpers (also used by the explanation service)
# ---------------------------------------------------------------------


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """Find the first JSON object in ``text`` and return it as a dict.

    Returns ``None`` if no valid JSON object is found.
    """
    candidate = (text or "").strip()
    if not candidate:
        return None

    parsed = _try_json(candidate)
    if parsed is not None:
        return parsed

    # ```json ... ``` fence.
    fence = re.search(
        r"```(?:json)?\s*(\{.*?\})\s*```",
        candidate,
        re.DOTALL,
    )
    if fence:
        parsed = _try_json(fence.group(1))
        if parsed is not None:
            return parsed

    first = candidate.find("{")
    last = candidate.rfind("}")
    if first != -1 and last > first:
        parsed = _try_json(candidate[first : last + 1])
        if parsed is not None:
            return parsed

    return None


def _try_json(text: str) -> dict[str, Any] | None:
    try:
        value = json.loads(text)
    except (ValueError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def _strip_colon_prefix(name: str) -> str:
    """Drop a leading ``:`` so ``:district_id`` and ``district_id``
    are interchangeable as parameter keys."""
    if not name:
        return name
    return name[1:] if name.startswith(":") else name


__all__ = [
    "ALLOWED_SQL_VERBS",
    "SQL_PROMPT_NAME",
    "SQLGenerationService",
    "_extract_json_object",
]
