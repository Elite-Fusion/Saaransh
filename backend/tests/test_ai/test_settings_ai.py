"""
Tests for the AI settings on :class:`backend.config.settings.Settings`.

The validator must:

  * accept a non-empty ``gemini_api_key`` (the happy path);
  * reject an empty ``gemini_api_key`` when
    ``ai_provider == "gemini"``;
  * accept the Phase 5 default model and overrides.

We mutate the cached settings instance (the conftest already
loaded it). Pydantic settings do not re-read the environment
on attribute access, so an in-place mutation is enough to
exercise the validator.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.config.settings import Settings


# ---------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------


class TestAISettingsDefaults:
    def test_ai_provider_default(self):
        s = Settings(
            gemini_api_key="k",
            gemini_model="gemini-2.0-flash",
        )
        assert s.ai_provider == "gemini"

    def test_default_model(self):
        s = Settings(
            gemini_api_key="k",
            gemini_model="gemini-2.0-flash",
        )
        assert s.gemini_model == "gemini-2.0-flash"

    def test_default_timeout(self):
        s = Settings(
            gemini_api_key="k",
            gemini_model="gemini-2.0-flash",
        )
        assert s.ai_request_timeout_seconds == 30.0

    def test_default_max_retries(self):
        s = Settings(
            gemini_api_key="k",
            gemini_model="gemini-2.0-flash",
        )
        assert s.ai_max_retries == 3

    def test_prompts_dir_default(self):
        s = Settings(
            gemini_api_key="k",
            gemini_model="gemini-2.0-flash",
        )
        assert s.ai_prompts_dir == ""


# ---------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------


class TestAISettingsValidation:
    def test_empty_gemini_key_rejected(self):
        with pytest.raises(ValidationError) as ei:
            Settings(
                ai_provider="gemini",
                gemini_api_key="",
                gemini_model="gemini-2.0-flash",
            )
        assert "GEMINI_API_KEY" in str(ei.value)

    def test_whitespace_only_gemini_key_rejected(self):
        with pytest.raises(ValidationError) as ei:
            Settings(
                ai_provider="gemini",
                gemini_api_key="   ",
                gemini_model="gemini-2.0-flash",
            )
        assert "GEMINI_API_KEY" in str(ei.value)

    def test_non_empty_key_accepted(self):
        s = Settings(
            ai_provider="gemini",
            gemini_api_key="real-key",
            gemini_model="gemini-2.0-flash",
        )
        assert s.gemini_api_key == "real-key"

    def test_zero_timeout_rejected(self):
        with pytest.raises(ValidationError):
            Settings(
                ai_provider="gemini",
                gemini_api_key="k",
                gemini_model="gemini-2.0-flash",
                ai_request_timeout_seconds=0,
            )

    def test_negative_retries_rejected(self):
        with pytest.raises(ValidationError):
            Settings(
                ai_provider="gemini",
                gemini_api_key="k",
                gemini_model="gemini-2.0-flash",
                ai_max_retries=-1,
            )

    def test_unsupported_provider_literal_rejected_by_settings(self):
        """``ai_provider`` is a ``Literal["gemini"]`` — any other
        value is rejected at the field level, before our validator
        runs."""
        with pytest.raises(ValidationError):
            Settings(
                ai_provider="claude",  # type: ignore[arg-type]
                gemini_api_key="k",
                gemini_model="gemini-2.0-flash",
            )
