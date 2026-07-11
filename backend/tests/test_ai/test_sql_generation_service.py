"""
Tests for :class:`backend.ai.services.sql_generation_service.SQLGenerationService`.

The service is a thin orchestrator over :class:`ChatService`: it
renders the SQL prompt, sends the question, parses the JSON reply
into a :class:`GeneratedSQL`, and normalises the parameter keys.

The tests cover:

  * happy path — the LLM returns clean JSON, the service returns a
    populated :class:`GeneratedSQL`;
  * fenced JSON (``json ... ``);
  * embedded JSON in prose;
  * empty SQL ("not a read query") — the service raises
    :class:`UnsafeSQL`;
  * unparseable reply — the service raises :class:`ProviderFailure`;
  * invalid schema (missing fields) — same outcome;
  * :class:`PromptNotFoundError` propagates as :class:`PromptError`;
  * :class:`AIProviderError` propagates as :class:`ProviderFailure`;
  * param keys with a leading colon are normalised.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from backend.ai.providers.errors import (
    AIProviderError,
    PromptNotFoundError,
)
from backend.ai.schemas.ai import GeneratedSQL
from backend.ai.services.exceptions import (
    PromptError,
    ProviderFailure,
    UnsafeSQL,
)
from backend.ai.services.sql_generation_service import (
    SQL_PROMPT_NAME,
    SQLGenerationService,
    _extract_json_object,
)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _gen_sql_json(
    *,
    sql: str = "SELECT CaseMasterID, CrimeNo FROM CaseMaster",
    params: dict | None = None,
    tables: list[str] | None = None,
    estimated_rows: str = "low",
    notes: str = "",
) -> str:
    return json.dumps(
        {
            "sql": sql,
            "params": params or {},
            "tables": tables or ["CaseMaster"],
            "estimated_rows": estimated_rows,
            "notes": notes,
        }
    )


@pytest.fixture
def chat_service(stub_chat_service):
    return stub_chat_service()


@pytest.fixture
def service(chat_service):
    return SQLGenerationService(chat_service=chat_service)


# ---------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------


class TestSQLGenerationHappyPath:
    def test_clean_json(self, service, chat_service, chat_response_factory):
        chat_service.chat_with_prompt.return_value = chat_response_factory(
            content=_gen_sql_json()
        )
        out = service.generate("List all cases.")
        assert isinstance(out, GeneratedSQL)
        assert out.sql == "SELECT CaseMasterID, CrimeNo FROM CaseMaster"
        assert out.tables == ["CaseMaster"]
        assert out.estimated_rows == "low"
        assert out.notes == ""

    def test_params_keys_stripped_of_colon(
        self, service, chat_service, chat_response_factory
    ):
        chat_service.chat_with_prompt.return_value = chat_response_factory(
            content=_gen_sql_json(
                sql="SELECT * FROM CaseMaster WHERE CaseMasterID = :id",
                params={":id": 12},
            )
        )
        out = service.generate("Case 12.")
        assert "id" in out.params
        assert ":id" not in out.params
        assert out.params["id"] == 12

    def test_fenced_json(self, service, chat_service, chat_response_factory):
        fenced = "```json\n" + _gen_sql_json(notes="fenced") + "\n```"
        chat_service.chat_with_prompt.return_value = chat_response_factory(
            content=fenced
        )
        out = service.generate("Anything.")
        assert out.notes == "fenced"

    def test_embedded_json(self, service, chat_service, chat_response_factory):
        reply = "Here you go:\n" + _gen_sql_json() + "\nThat should work."
        chat_service.chat_with_prompt.return_value = chat_response_factory(
            content=reply
        )
        out = service.generate("Anything.")
        assert out.sql.startswith("SELECT")

    def test_schema_summary_passed_to_prompt(
        self, service, chat_service, chat_response_factory
    ):
        chat_service.chat_with_prompt.return_value = chat_response_factory(
            content=_gen_sql_json()
        )
        service.generate("Anything.")
        kwargs = chat_service.chat_with_prompt.call_args.kwargs
        assert "SCHEMA_SUMMARY" in kwargs
        assert "QUESTION" in kwargs


# ---------------------------------------------------------------------
# Empty SQL — model refused
# ---------------------------------------------------------------------


class TestSQLGenerationEmptySQL:
    def test_empty_sql_raises_unsafe(self, service, chat_service, chat_response_factory):
        chat_service.chat_with_prompt.return_value = chat_response_factory(
            content=json.dumps(
                {
                    "sql": "",
                    "params": {},
                    "tables": [],
                    "estimated_rows": "unknown",
                    "notes": "request is not a read query",
                }
            )
        )
        with pytest.raises(UnsafeSQL) as ei:
            service.generate("Tell me a joke.")
        assert ei.value.category == "empty_sql"

    def test_whitespace_sql_raises_unsafe(
        self, service, chat_service, chat_response_factory
    ):
        chat_service.chat_with_prompt.return_value = chat_response_factory(
            content=json.dumps(
                {
                    "sql": "   ",
                    "params": {},
                    "tables": [],
                    "estimated_rows": "unknown",
                    "notes": "no read query possible",
                }
            )
        )
        with pytest.raises(UnsafeSQL):
            service.generate("Tell me a joke.")


# ---------------------------------------------------------------------
# Parse failure
# ---------------------------------------------------------------------


class TestSQLGenerationParseFailure:
    def test_unparseable_raises_provider_failure(
        self, service, chat_service, chat_response_factory
    ):
        chat_service.chat_with_prompt.return_value = chat_response_factory(
            content="Sorry, I cannot help with that."
        )
        with pytest.raises(ProviderFailure) as ei:
            service.generate("Anything.")
        assert "JSON" in str(ei.value)

    def test_invalid_schema_raises_provider_failure(
        self, service, chat_service, chat_response_factory
    ):
        chat_service.chat_with_prompt.return_value = chat_response_factory(
            content=json.dumps({"foo": "bar"})  # missing 'sql'
        )
        with pytest.raises(ProviderFailure) as ei:
            service.generate("Anything.")
        assert "schema" in str(ei.value).lower()

    def test_wrong_type_raises_provider_failure(
        self, service, chat_service, chat_response_factory
    ):
        chat_service.chat_with_prompt.return_value = chat_response_factory(
            content=json.dumps({"sql": 123, "params": {}, "tables": []})
        )
        with pytest.raises(ProviderFailure):
            service.generate("Anything.")


# ---------------------------------------------------------------------
# LLM raises
# ---------------------------------------------------------------------


class TestSQLGenerationLLMFailure:
    def test_provider_error_propagates(
        self, service, chat_service
    ):
        chat_service.chat_with_prompt.side_effect = AIProviderError(
            "rate limited", provider="gemini"
        )
        with pytest.raises(ProviderFailure) as ei:
            service.generate("Anything.")
        assert "rate limited" in str(ei.value)
        assert ei.value.provider == "gemini"

    def test_prompt_not_found_propagates(
        self, service, chat_service
    ):
        chat_service.chat_with_prompt.side_effect = PromptNotFoundError(
            SQL_PROMPT_NAME
        )
        with pytest.raises(PromptError) as ei:
            service.generate("Anything.")
        assert ei.value.prompt_name == SQL_PROMPT_NAME


# ---------------------------------------------------------------------
# Schema summary caching
# ---------------------------------------------------------------------


class TestSQLGenerationSchemaSummary:
    def test_explicit_summary_used(
        self, chat_service
    ):
        service = SQLGenerationService(
            chat_service=chat_service, schema_summary="MY_SUMMARY"
        )
        assert service.schema_summary == "MY_SUMMARY"

    def test_default_summary_built_lazily(
        self, service
    ):
        # The default summary mentions every allowlisted table.
        summary = service.schema_summary
        assert "CaseMaster" in summary
        assert "Accused" in summary
        assert "Victim" in summary


# ---------------------------------------------------------------------
# _extract_json_object — the heart of the JSON parser
# ---------------------------------------------------------------------


class TestExtractJSONObject:
    def test_raw(self):
        text = json.dumps({"intent": "x"})
        assert _extract_json_object(text) == {"intent": "x"}

    def test_fenced(self):
        text = "```json\n" + json.dumps({"a": 1}) + "\n```"
        assert _extract_json_object(text) == {"a": 1}

    def test_fenced_no_lang(self):
        text = "```\n" + json.dumps({"a": 1}) + "\n```"
        assert _extract_json_object(text) == {"a": 1}

    def test_embedded_in_prose(self):
        text = "Sure! " + json.dumps({"a": 2}) + " Done."
        assert _extract_json_object(text) == {"a": 2}

    def test_returns_none_on_empty(self):
        assert _extract_json_object("") is None

    def test_returns_none_on_non_dict(self):
        assert _extract_json_object("[1, 2, 3]") is None

    def test_returns_none_on_garbage(self):
        assert _extract_json_object("not json at all") is None
