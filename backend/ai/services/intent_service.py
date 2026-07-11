"""
IntentService — classify an officer's question into one of six buckets.

The service is the first stage of the investigation pipeline (see the
architecture diagram in :file:`backend/ai/README.md`). It calls
:class:`~backend.ai.services.chat_service.ChatService` to render the
:class:`backend.ai.prompts.intent_prompt` and ask Gemini to label the
question. A regex/keyword fallback catches the obvious cases
(``"investigate case 12"``) so a misbehaving LLM never makes the
service useless.

The service is **provider-agnostic** and **FastAPI-independent** —
it only depends on :class:`ChatService`. Tests inject a stub
:class:`ChatService` that returns a canned response; the real
production path uses the singleton from
:func:`backend.ai.services.get_prompt_service` /
:func:`backend.ai.providers.get_provider`.

Failure modes:

  * The LLM returns garbage that cannot be JSON-parsed. The
    service falls through to the keyword regex.
  * The keyword regex also matches nothing. The service raises
    :class:`~backend.ai.services.exceptions.UnknownIntent`.
  * The :class:`ChatService` raises an :class:`AIProviderError`.
    The service wraps it as :class:`ProviderFailure`.
  * A :class:`PromptNotFoundError` propagates as :class:`PromptError`.
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
    Intent,
    IntentClassification,
)
from backend.ai.services.chat_service import ChatService
from backend.ai.services.exceptions import (
    PromptError,
    ProviderFailure,
    UnknownIntent,
)

#: Stem of the intent prompt file in
#: :file:`backend/ai/prompts/`. Resolved by :class:`PromptService` at
#: runtime — never hardcode the path.
INTENT_PROMPT_NAME = "intent_prompt"

#: Cap on the raw LLM response we keep in
#: :attr:`IntentClassification.raw_response` for the audit log.
_RAW_RESPONSE_CAP = 500

# ---------------------------------------------------------------------
# Regex / keyword fallback
# ---------------------------------------------------------------------
#
# The fallback only fires when the LLM call failed. It uses a small
# set of carefully ordered patterns. A more aggressive regex layer
# would risk misclassifying "show me a similar case" as `case_search`
# when the user actually wants `similar_cases` — order matters.

_CASE_ID_RE = re.compile(r"\bcase\s*(?:id\s*[:=]?\s*)?(\d+)\b", re.IGNORECASE)
_FIR_RE = re.compile(r"\bFIR\s*(?:number\s*[:=]?\s*)?([A-Z0-9]+)\b", re.IGNORECASE)

_INVESTIGATE_RE = re.compile(
    r"\b(investigate|investigation\s+brief|investigation\s+summary|"
    r"give\s+me\s+a\s+brief|all\s+about|everything\s+about)\b",
    re.IGNORECASE,
)
_EXPLAIN_RE = re.compile(
    r"\b(what\s+happened|explain|summarise|summarize|"
    r"describe|narrative|story\s+of|background\s+of)\b",
    re.IGNORECASE,
)
_SIMILAR_RE = re.compile(
    r"\b(similar\s+(?:cases?|mos?|offences?|crimes?|incidents?)|"
    r"repeat\s+offen(?:der|ce|ces)|same\s+mo|like\s+this\s+one|"
    r"resemble|resembling)\b",
    re.IGNORECASE,
)
_DASHBOARD_RE = re.compile(
    r"\b(how\s+many|trend|trends|distribution|breakdown|"
    r"summary\s+of\s+(?:cases|the\s+database)|overall|"
    r"monthly|quarterly|annual\s+stats?|statistics)\b",
    re.IGNORECASE,
)
_CASE_LIST_RE = re.compile(
    r"\b(list|show|find|fetch|get|search\s+for)\s+"
    r"(?:all\s+)?(?:the\s+)?(?:cases?|firs?|incidents?)\b",
    re.IGNORECASE,
)

#: Minimum length of a question that the fallback will try. Below
#: this we treat the input as too short to be a real investigation
#: question and return UNKNOWN.
_MIN_QUESTION_LEN = 8


class IntentService:
    """Classify an officer's question into an :class:`Intent`.

    Args:
        chat_service: The :class:`ChatService` the service delegates
            to. Typically the production singleton.
        logger: Optional :class:`logging.Logger`. Defaults to a
            module-level logger.
    """

    def __init__(
        self,
        *,
        chat_service: ChatService,
        logger: logging.Logger | None = None,
    ) -> None:
        self._chat = chat_service
        self._logger = logger or logging.getLogger(
            "backend.ai.services.intent_service"
        )

    # ------------------------------------------------------------------
    # Public surface
    # ------------------------------------------------------------------

    def classify(
        self,
        question: str,
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> IntentClassification:
        """Classify ``question`` and return an :class:`IntentClassification`.

        Args:
            question: The officer's natural-language question.
            metadata: Optional metadata dict propagated to the LLM
                call. Useful for request ids, officer ids, etc.

        Returns:
            A populated :class:`IntentClassification`.

        Raises:
            UnknownIntent: The LLM and the regex fallback both
                returned ``UNKNOWN``. The route layer maps this to 400.
            PromptError: The intent prompt file is missing on disk.
            ProviderFailure: The :class:`ChatService` raised.
        """
        question = (question or "").strip()
        if len(question) < _MIN_QUESTION_LEN:
            self._logger.info(
                "intent_short_circuit question_chars=%d",
                len(question),
            )
            raise UnknownIntent(
                question,
                reason="Question is too short to classify.",
            )

        llm_result: IntentClassification | None = None
        try:
            llm_result = self._classify_with_llm(question, metadata)
        except (ProviderFailure, PromptError) as exc:
            self._logger.info(
                "intent_llm_failed_falling_back error=%s",
                type(exc).__name__,
            )
            # Fall through to the regex path.

        if llm_result is not None and llm_result.intent is not Intent.UNKNOWN:
            return llm_result

        # Fallback (also runs when LLM returned UNKNOWN).
        fallback_intent, fallback_reason = self._classify_with_regex(question)
        if fallback_intent is Intent.UNKNOWN:
            self._logger.info(
                "intent_unknown question=%r", question[:200]
            )
            raise UnknownIntent(question, reason=fallback_reason)

        # The LLM at least partially understood the question — keep
        # its reasoning if it had one.
        llm_reasoning = llm_result.reasoning if llm_result else ""
        return IntentClassification(
            intent=fallback_intent,
            confidence=0.5,  # regex path is heuristic
            reasoning=fallback_reason or llm_reasoning or "regex fallback",
            raw_response=llm_result.raw_response if llm_result else "",
        )

    # ------------------------------------------------------------------
    # LLM path
    # ------------------------------------------------------------------

    def _classify_with_llm(
        self,
        question: str,
        metadata: Mapping[str, Any] | None,
    ) -> IntentClassification:
        """Render the prompt, call the LLM, parse the JSON reply."""
        try:
            response = self._chat.chat_with_prompt(
                INTENT_PROMPT_NAME,
                question,
                temperature=0.0,  # classification should be deterministic
                max_output_tokens=256,
                metadata=dict(metadata or {}),
            )
        except PromptNotFoundError as exc:
            raise PromptError(
                INTENT_PROMPT_NAME, original=exc
            ) from exc
        except AIProviderError as exc:
            raise ProviderFailure(
                f"LLM call failed: {exc}",
                original=exc,
                provider=getattr(exc, "provider", None),
            ) from exc

        raw = response.content or ""
        parsed = self._parse_llm_reply(raw)
        if parsed is None:
            self._logger.info(
                "intent_llm_unparseable raw=%r", raw[:200]
            )
            # Return an UNKNOWN classification so the caller falls
            # through to the regex path. Keep the raw response for
            # the audit log.
            return IntentClassification(
                intent=Intent.UNKNOWN,
                confidence=0.0,
                reasoning="LLM reply was not valid JSON.",
                raw_response=raw[:_RAW_RESPONSE_CAP],
            )

        try:
            return IntentClassification(
                intent=Intent(parsed["intent"]),
                confidence=float(parsed.get("confidence", 0.5)),
                reasoning=str(parsed.get("reasoning", "")).strip() or "no reasoning",
                raw_response=raw[:_RAW_RESPONSE_CAP],
            )
        except (KeyError, ValueError, ValidationError) as exc:
            self._logger.info(
                "intent_llm_invalid_schema error=%s raw=%r",
                type(exc).__name__,
                raw[:200],
            )
            return IntentClassification(
                intent=Intent.UNKNOWN,
                confidence=0.0,
                reasoning=f"LLM reply did not match the schema: {exc}",
                raw_response=raw[:_RAW_RESPONSE_CAP],
            )

    @staticmethod
    def _parse_llm_reply(text: str) -> dict[str, Any] | None:
        """Extract a JSON object from the LLM reply.

        The model is asked to return JSON only, but Gemini often wraps
        it in ```json ... ``` fences. We try:
          1. the raw text;
          2. the first fenced block (``json { ... } ``);
          3. the substring between the first ``{`` and the last ``}``.
        """
        candidate = (text or "").strip()
        if not candidate:
            return None

        # 1. raw
        parsed = _try_json(candidate)
        if parsed is not None:
            return parsed

        # 2. fenced ```json ... ``` block
        fence = re.search(
            r"```(?:json)?\s*(\{.*?\})\s*```",
            candidate,
            re.DOTALL,
        )
        if fence:
            parsed = _try_json(fence.group(1))
            if parsed is not None:
                return parsed

        # 3. first '{' to last '}'
        first = candidate.find("{")
        last = candidate.rfind("}")
        if first != -1 and last > first:
            parsed = _try_json(candidate[first : last + 1])
            if parsed is not None:
                return parsed

        return None

    # ------------------------------------------------------------------
    # Regex fallback
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_with_regex(question: str) -> tuple[Intent, str]:
        """Heuristic classification.

        Order matters: ``investigation_summary`` and ``explain_case``
        both look for a case id, but the trigger phrases differ. We
        check ``investigate`` / "brief" / "everything about" first
        because those outrank the generic "explain" trigger.
        """
        if not question:
            return Intent.UNKNOWN, "empty question"

        if _INVESTIGATE_RE.search(question):
            return (
                Intent.INVESTIGATION_SUMMARY,
                "Question uses an investigation trigger phrase.",
            )
        if _SIMILAR_RE.search(question):
            return (
                Intent.SIMILAR_CASES,
                "Question uses a similar-case trigger phrase.",
            )
        if _EXPLAIN_RE.search(question) and (
            _CASE_ID_RE.search(question) or _FIR_RE.search(question)
        ):
            return (
                Intent.EXPLAIN_CASE,
                "Question uses an explain trigger plus a case reference.",
            )
        if _DASHBOARD_RE.search(question):
            return (
                Intent.DASHBOARD_ANALYTICS,
                "Question uses a dashboard / analytics trigger phrase.",
            )
        if _CASE_LIST_RE.search(question):
            return (
                Intent.CASE_SEARCH,
                "Question uses a case-list trigger phrase.",
            )
        if _CASE_ID_RE.search(question) or _FIR_RE.search(question):
            # Bare case id — most officers mean "explain" when they
            # say "case 47" with no verb.
            return (
                Intent.EXPLAIN_CASE,
                "Question references a specific case id / FIR number.",
            )
        return Intent.UNKNOWN, "no trigger phrase matched"


def _try_json(text: str) -> dict[str, Any] | None:
    """Return the parsed JSON or ``None`` on any error."""
    try:
        value = json.loads(text)
    except (ValueError, TypeError):
        return None
    return value if isinstance(value, dict) else None


__all__ = ["IntentService", "INTENT_PROMPT_NAME"]
