"""
PromptService — loads and renders prompt templates from
``backend/ai/prompts/*.md``.

The service exists for one reason: **no prompt is hardcoded in
Python**. Every prompt is a file in :mod:`backend.ai.prompts`,
read at runtime, cached, and rendered with
:py:meth:`str.format`. Tests and production use the same code
path — never a literal string in a ``.py`` file.

The service is provider-agnostic and FastAPI-independent. It
takes the prompts directory in its constructor and exposes:

  * :meth:`load(name)` — return the raw contents of a prompt
    file (cached).
  * :meth:`render(name, **vars)` — load + ``str.format(**vars)``.
  * :meth:`clear_cache()` — test helper.

The service never logs prompt content. CLAUDE.md's
"Never log API keys" rule generalises to PII / sensitive
context — prompt bodies can contain user data the model is
about to process, and a careless ``logger.debug(prompt)`` is
the kind of leak we want to make impossible.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.ai.providers.errors import PromptNotFoundError

_LOGGER = logging.getLogger("backend.ai.services.prompt_service")

#: Default location of the prompt templates, resolved relative to
#: this file's location. ``backend/ai/services/prompt_service.py``
#: lives two levels below ``backend/ai/prompts/``.
_DEFAULT_PROMPTS_DIR = (
    Path(__file__).resolve().parent.parent / "prompts"
)


class PromptService:
    """Loads and renders prompt templates from a directory of ``.md`` files.

    Args:
        prompts_dir: The directory to read prompts from. Defaults to
            ``backend/ai/prompts/`` (resolved from this module's
            location). Pass an explicit value in tests so the
            service can be exercised against a ``tmp_path`` fixture
            without touching the real prompt files.
    """

    def __init__(self, prompts_dir: Path | str | None = None) -> None:
        self._prompts_dir = (
            Path(prompts_dir) if prompts_dir is not None else _DEFAULT_PROMPTS_DIR
        )
        # Per-instance cache, keyed by file stem (the part before
        # ``.md``). lru_cache on a method is awkward when tests
        # want to swap the directory out from under us, so a plain
        # dict + a public ``clear_cache`` is cleaner.
        self._cache: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Public surface
    # ------------------------------------------------------------------

    def load(self, name: str) -> str:
        """Return the raw contents of the prompt file ``name``.

        Args:
            name: The file stem, with or without the ``.md``
                suffix. ``"system_prompt"`` and
                ``"system_prompt.md"`` are equivalent.

        Returns:
            The full file contents as a UTF-8 string.

        Raises:
            PromptNotFoundError: No file matching ``name`` exists
                in the configured prompts directory.
        """
        key = self._normalise_name(name)
        if key in self._cache:
            return self._cache[key]

        path = self._resolve_path(key)
        if path is None or not path.is_file():
            raise PromptNotFoundError(
                name, prompts_dir=str(self._prompts_dir)
            )

        text = path.read_text(encoding="utf-8")
        self._cache[key] = text
        _LOGGER.info(
            "prompt_loaded name=%s size_chars=%d", key, len(text)
        )
        return text

    def render(self, name: str, **vars: Any) -> str:
        """Load a prompt and apply :py:meth:`str.format` substitutions.

        Args:
            name: The prompt file stem.
            **vars: Keyword arguments substituted into the prompt
                template's ``{{NAME}}`` placeholders. Every
                placeholder referenced by the template must be
                supplied; missing keys raise :class:`KeyError`.

        Returns:
            The rendered prompt as a single string.

        Raises:
            PromptNotFoundError: ``name`` does not match a file.
            KeyError: A placeholder in the template has no matching
                keyword in ``vars``. Letting this propagate keeps
                the failure mode obvious — a missing variable in a
                prompt is a programmer error, not a runtime one.
        """
        template = self.load(name)
        return template.format(**vars)

    def clear_cache(self) -> None:
        """Drop every cached prompt. Test helper."""
        self._cache.clear()

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def prompts_dir(self) -> Path:
        """The directory this service reads prompts from."""
        return self._prompts_dir

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"PromptService(prompts_dir={str(self._prompts_dir)!r}, "
            f"cached={len(self._cache)})"
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_name(name: str) -> str:
        """Strip the ``.md`` suffix and any path components."""
        if not name:
            raise PromptNotFoundError(name)
        # Allow callers to pass ``foo.md`` or ``foo`` interchangeably.
        cleaned = name.strip()
        if cleaned.lower().endswith(".md"):
            cleaned = cleaned[:-3]
        # Reject path traversal — the prompt name is not a path.
        if "/" in cleaned or "\\" in cleaned or cleaned.startswith(".."):
            raise PromptNotFoundError(name)
        return cleaned

    def _resolve_path(self, key: str) -> Path | None:
        """Return the candidate path for ``key`` (no IO)."""
        if not self._prompts_dir.exists() or not self._prompts_dir.is_dir():
            return None
        return self._prompts_dir / f"{key}.md"


# ---------------------------------------------------------------------
# Process-wide singleton
# ---------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_prompt_service() -> PromptService:
    """Return the process-wide :class:`PromptService`.

    :class:`ChatService` and the future route layer should
    inject the service through their constructors. This
    function is provided for the rare case where a caller has
    no DI container handy (scripts, REPL).
    """
    return PromptService()


def reset_prompt_service_cache() -> None:
    """Drop the cached singleton. Test-only helper."""
    get_prompt_service.cache_clear()


__all__ = ["PromptService", "get_prompt_service", "reset_prompt_service_cache"]
