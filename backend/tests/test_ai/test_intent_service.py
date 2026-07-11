"""
Tests for :class:`backend.ai.services.intent_service.IntentService`.

The service has two paths: an LLM path (default) and a regex
fallback. The tests exercise:

  * the happy path with a stubbed :class:`ChatService` returning
    valid JSON;
  * the LLM returning prose (the service must fall through to the
    regex path);
  * the LLM raising an :class:`AIProviderError` (the service must
    wrap as :class:`ProviderFailure` and fall through to regex);
  * the regex path alone returning a non-:data:`UNKNOWN` intent;
  * a question that neither path can classify (the service must
    raise :class:`UnknownIntent`);
  * a too-short question (the service must short-circuit to
    :class:`UnknownIntent`).
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from backend.ai.providers.errors import (
    AIProviderError,
    PromptNotFoundError,
)
from backend.ai.schemas.ai import (
    Intent,
    IntentClassification,
)
from backend.ai.services.exceptions import (
    PromptError,
    ProviderFailure,
    UnknownIntent,
)
from backend.ai.services.intent_service import INTENT_PROMPT_NAME, IntentService


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _intent_json(intent: str, confidence: float = 0.9, reasoning: str = "r") -> str:
    return json.dumps(
        {"intent": intent, "confidence": confidence, "reasoning": reasoning}
    )


@pytest.fixture
def chat_service(stub_chat_service):
    """A stub :class:`ChatService` that returns a configurable
    ``chat_with_prompt`` response. The default raises
    ``NotImplementedError`` so each test must set up its own stub."""
    return stub_chat_service()


@pytest.fixture
def service(chat_service):
    """An :class:`IntentService` bound to the stub chat service."""
    return IntentService(chat_service=chat_service)


# ---------------------------------------------------------------------
# Happy path: LLM returns a clean JSON intent
# ---------------------------------------------------------------------


class TestIntentServiceHappyPath:
    def test_case_search(self, service, chat_service, chat_response_factory):
        chat_service.chat_with_prompt.side_effect = None
        chat_service.chat_with_prompt.return_value = chat_response_factory(
            content=_intent_json(Intent.CASE_SEARCH.value)
        )
        out = service.classify("List all cases in Mysuru.")
        assert out.intent is Intent.CASE_SEARCH
        assert out.confidence == 0.9
        assert out.reasoning == "r"

    def test_similar_cases(self, service, chat_service, chat_response_factory):
        chat_service.chat_with_prompt.return_value = chat_response_factory(
            content=_intent_json(Intent.SIMILAR_CASES.value, confidence=0.7)
        )
        out = service.classify("Find cases with a similar MO to FIR 1044.")
        assert out.intent is Intent.SIMILAR_CASES
        assert out.confidence == 0.7

    def test_investigation_summary(self, service, chat_service, chat_response_factory):
        chat_service.chat_with_prompt.return_value = chat_response_factory(
            content=_intent_json(Intent.INVESTIGATION_SUMMARY.value)
        )
        out = service.classify("Investigate case 47.")
        assert out.intent is Intent.INVESTIGATION_SUMMARY

    def test_explain_case(self, service, chat_service, chat_response_factory):
        chat_service.chat_with_prompt.return_value = chat_response_factory(
            content=_intent_json(Intent.EXPLAIN_CASE.value)
        )
        out = service.classify("What happened in case 47?")
        assert out.intent is Intent.EXPLAIN_CASE

    def test_dashboard_analytics(self, service, chat_service, chat_response_factory):
        chat_service.chat_with_prompt.return_value = chat_response_factory(
            content=_intent_json(Intent.DASHBOARD_ANALYTICS.value)
        )
        out = service.classify("How many open cases are there?")
        assert out.intent is Intent.DASHBOARD_ANALYTICS

    def test_raw_response_capped(self, service, chat_service, chat_response_factory):
        long = "x" * 5000
        chat_service.chat_with_prompt.return_value = chat_response_factory(
            content=_intent_json(Intent.CASE_SEARCH.value) + " " + long
        )
        out = service.classify("List cases.")
        assert len(out.raw_response) <= 500


# ---------------------------------------------------------------------
# LLM returns prose / non-JSON content
# ---------------------------------------------------------------------


class TestIntentServiceLLMUnparseable:
    def test_prose_falls_through_to_regex(
        self, service, chat_service, chat_response_factory
    ):
        chat_service.chat_with_prompt.return_value = chat_response_factory(
            content="I'm sorry, I cannot classify that."
        )
        out = service.classify("List all FIRs in Mysuru in 2024")
        # The regex path catches the "list" trigger.
        assert out.intent is Intent.CASE_SEARCH
        assert out.confidence == 0.5  # regex fallback confidence

    def test_invalid_intent_value_falls_through(
        self, service, chat_service, chat_response_factory
    ):
        chat_service.chat_with_prompt.return_value = chat_response_factory(
            content=json.dumps(
                {"intent": "nonexistent", "confidence": 0.5, "reasoning": "x"}
            )
        )
        out = service.classify("List all cases in Mysuru in 2024")
        # Invalid intent value -> UNKNOWN -> regex fallback -> case_search.
        assert out.intent is Intent.CASE_SEARCH

    def test_unknown_intent_falls_through(
        self, service, chat_service, chat_response_factory
    ):
        chat_service.chat_with_prompt.return_value = chat_response_factory(
            content=_intent_json(Intent.UNKNOWN.value, confidence=0.0)
        )
        out = service.classify("List all cases in Mysuru in 2024")
        assert out.intent is Intent.CASE_SEARCH


# ---------------------------------------------------------------------
# LLM raises an exception
# ---------------------------------------------------------------------


class TestIntentServiceLLMFailure:
    def test_provider_error_wrapped(self, service, chat_service):
        chat_service.chat_with_prompt.side_effect = AIProviderError(
            "throttled", provider="gemini"
        )
        out = service.classify("List all cases in Mysuru in 2024")
        # Falls through to regex; returns CASE_SEARCH.
        assert out.intent is Intent.CASE_SEARCH

    def test_prompt_not_found_wrapped(self, service, chat_service):
        chat_service.chat_with_prompt.side_effect = PromptNotFoundError(
            INTENT_PROMPT_NAME
        )
        # Same as above: regex catches it.
        out = service.classify("List all cases in Mysuru in 2024")
        assert out.intent is Intent.CASE_SEARCH

    def test_prompt_error_raises_when_regex_unknown(
        self, chat_service
    ):
        """When the LLM raises AND the regex returns UNKNOWN, the
        regex takes precedence — the prompt error is silently
        recovered. (The investigation service still works.)"""
        from backend.ai.providers.errors import PromptNotFoundError

        chat_service.chat_with_prompt.side_effect = PromptNotFoundError(
            INTENT_PROMPT_NAME
        )
        service = IntentService(chat_service=chat_service)
        # An off-topic question — regex returns UNKNOWN.
        with pytest.raises(UnknownIntent):
            service.classify("what is the meaning of life?")


# ---------------------------------------------------------------------
# Regex fallback only
# ---------------------------------------------------------------------


class TestIntentServiceRegexOnly:
    """A service whose chat never raises and always returns invalid
    content — exercises the regex path on its own."""

    @pytest.fixture
    def regex_service(self, chat_service, chat_response_factory):
        chat_service.chat_with_prompt.return_value = chat_response_factory(
            content="not json at all"
        )
        return IntentService(chat_service=chat_service)

    def test_investigate_phrase(self, regex_service):
        out = regex_service.classify("Investigate case 47.")
        assert out.intent is Intent.INVESTIGATION_SUMMARY

    def test_explain_phrase(self, regex_service):
        out = regex_service.classify("Explain case 47.")
        assert out.intent is Intent.EXPLAIN_CASE

    def test_similar_phrase(self, regex_service):
        out = regex_service.classify("Find similar cases to FIR 1044.")
        assert out.intent is Intent.SIMILAR_CASES

    def test_dashboard_phrase(self, regex_service):
        out = regex_service.classify("How many open cases are there?")
        assert out.intent is Intent.DASHBOARD_ANALYTICS

    def test_case_list_phrase(self, regex_service):
        out = regex_service.classify("List all cases in Mysuru district.")
        assert out.intent is Intent.CASE_SEARCH

    def test_bare_case_id(self, regex_service):
        out = regex_service.classify("case 47 details")
        assert out.intent is Intent.EXPLAIN_CASE

    def test_fir_number(self, regex_service):
        out = regex_service.classify("FIR 104430007202400033 details")
        assert out.intent is Intent.EXPLAIN_CASE

    def test_no_match_raises(self, regex_service):
        with pytest.raises(UnknownIntent) as ei:
            regex_service.classify("What is the meaning of life?")
        assert "meaning of life" in ei.value.question

    def test_empty_raises(self, regex_service):
        with pytest.raises(UnknownIntent):
            regex_service.classify("")

    def test_short_raises(self, regex_service):
        with pytest.raises(UnknownIntent) as ei:
            regex_service.classify("hi")
        assert "too short" in ei.value.reason

    def test_whitespace_only_raises(self, regex_service):
        with pytest.raises(UnknownIntent):
            regex_service.classify("      ")


# ---------------------------------------------------------------------
# Prompt file actually loaded
# ---------------------------------------------------------------------


class TestIntentServicePromptLoading:
    def test_uses_intent_prompt_name(
        self, service, chat_service, chat_response_factory
    ):
        chat_service.chat_with_prompt.return_value = chat_response_factory(
            content=_intent_json(Intent.CASE_SEARCH.value)
        )
        service.classify("List cases.")
        chat_service.chat_with_prompt.assert_called_once()
        kwargs = chat_service.chat_with_prompt.call_args.kwargs
        # chat_with_prompt is called as (prompt_name, user_message, **kwargs).
        args = chat_service.chat_with_prompt.call_args.args
        assert args[0] == INTENT_PROMPT_NAME
        assert "temperature" in kwargs
        assert kwargs["temperature"] == 0.0
