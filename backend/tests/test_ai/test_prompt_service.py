"""
PromptService tests.

The service is responsible for two contracts:

  * Load a Markdown file from ``backend/ai/prompts/`` and
    return its contents.
  * Render the file with ``str.format(**vars)``.

A ``PromptNotFoundError`` is raised when the file is missing;
a ``KeyError`` propagates when a placeholder has no
corresponding variable.
"""
from __future__ import annotations

import pytest

from backend.ai.providers.errors import PromptNotFoundError
from backend.ai.services.prompt_service import PromptService


# ---------------------------------------------------------------------
# load(name)
# ---------------------------------------------------------------------


class TestPromptServiceLoad:
    def test_load_returns_file_contents(self, tmp_prompts_dir):
        service = PromptService(prompts_dir=tmp_prompts_dir)
        assert service.load("hello") == "Hello {officer_name}! Today is {weekday}."

    def test_load_accepts_md_suffix(self, tmp_prompts_dir):
        service = PromptService(prompts_dir=tmp_prompts_dir)
        assert service.load("hello.md") == "Hello {officer_name}! Today is {weekday}."

    def test_load_caches(self, tmp_prompts_dir):
        service = PromptService(prompts_dir=tmp_prompts_dir)
        first = service.load("hello")
        # Mutate the file on disk; the cached value must not change.
        (tmp_prompts_dir / "hello.md").write_text("MUTATED", encoding="utf-8")
        second = service.load("hello")
        assert first == second

    def test_load_missing_raises(self, tmp_prompts_dir):
        service = PromptService(prompts_dir=tmp_prompts_dir)
        with pytest.raises(PromptNotFoundError) as exc:
            service.load("does_not_exist")
        assert exc.value.name == "does_not_exist"
        assert str(tmp_prompts_dir) in str(exc.value)

    def test_load_rejects_path_traversal(self, tmp_prompts_dir):
        service = PromptService(prompts_dir=tmp_prompts_dir)
        with pytest.raises(PromptNotFoundError):
            service.load("../etc/passwd")
        with pytest.raises(PromptNotFoundError):
            service.load("..\\windows\\system32")

    def test_load_empty_name_raises(self, tmp_prompts_dir):
        service = PromptService(prompts_dir=tmp_prompts_dir)
        with pytest.raises(PromptNotFoundError):
            service.load("")

    def test_clear_cache_re_reads(self, tmp_prompts_dir):
        service = PromptService(prompts_dir=tmp_prompts_dir)
        first = service.load("hello")
        (tmp_prompts_dir / "hello.md").write_text("CHANGED", encoding="utf-8")
        service.clear_cache()
        assert service.load("hello") == "CHANGED"

    def test_missing_directory_does_not_crash(self, tmp_path):
        """A missing prompts directory surfaces as PromptNotFoundError,
        not a FileNotFoundError — never let the AI layer crash on
        a bad config."""
        service = PromptService(prompts_dir=tmp_path / "does_not_exist")
        with pytest.raises(PromptNotFoundError):
            service.load("anything")


# ---------------------------------------------------------------------
# render(name, **vars)
# ---------------------------------------------------------------------


class TestPromptServiceRender:
    def test_render_substitutes_placeholders(self, tmp_prompts_dir):
        service = PromptService(prompts_dir=tmp_prompts_dir)
        out = service.render("hello", officer_name="Officer", weekday="Monday")
        assert out == "Hello Officer! Today is Monday."

    def test_render_missing_var_raises_keyerror(self, tmp_prompts_dir):
        service = PromptService(prompts_dir=tmp_prompts_dir)
        with pytest.raises(KeyError):
            # ``weekday`` not supplied.
            service.render("hello", officer_name="Officer")

    def test_render_no_placeholders(self, tmp_prompts_dir):
        service = PromptService(prompts_dir=tmp_prompts_dir)
        assert service.render("no_vars") == "Static prompt, no vars."

    def test_render_missing_prompt_propagates(self, tmp_prompts_dir):
        service = PromptService(prompts_dir=tmp_prompts_dir)
        with pytest.raises(PromptNotFoundError):
            service.render("does_not_exist", foo="bar")

    def test_render_caches_load(self, tmp_prompts_dir):
        service = PromptService(prompts_dir=tmp_prompts_dir)
        first = service.render("hello", officer_name="A", weekday="B")
        # Mutate file; cache must hold.
        (tmp_prompts_dir / "hello.md").write_text("MUTATED", encoding="utf-8")
        second = service.render("hello", officer_name="A", weekday="B")
        assert first == second
        assert second == "Hello A! Today is B."


# ---------------------------------------------------------------------
# Process-wide singleton
# ---------------------------------------------------------------------


class TestPromptServiceSingleton:
    def test_get_prompt_service_returns_singleton(self):
        from backend.ai.services.prompt_service import (
            get_prompt_service,
            reset_prompt_service_cache,
        )

        reset_prompt_service_cache()
        a = get_prompt_service()
        b = get_prompt_service()
        assert a is b
        reset_prompt_service_cache()

    def test_default_prompts_dir_resolves(self):
        """The default constructor must find the shipped prompts."""
        from backend.ai.services.prompt_service import (
            get_prompt_service,
            reset_prompt_service_cache,
        )

        reset_prompt_service_cache()
        try:
            service = get_prompt_service()
            for name in (
                "system_prompt",
                "sql_prompt",
                "explanation_prompt",
                "investigation_prompt",
            ):
                text = service.load(name)
                assert text.strip(), f"Prompt {name!r} is empty"
        finally:
            reset_prompt_service_cache()
