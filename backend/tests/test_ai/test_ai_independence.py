"""
AI-layer independence tests.

Mirrors ``tests/test_service_independence.py``: AST-scan every
Python file under ``backend/ai/`` for forbidden
``fastapi`` / ``starlette`` imports. Catches the two most
likely regressions before they reach production:

  * a service decides to import ``fastapi`` for typing;
  * a prompt helper starts using ``BackgroundTasks``.

Phase 6 also adds a stricter check: no file under ``backend/ai/``
may import the database-touching service modules
(``backend.services.sql_executor`` or
``backend.services.ai_query_service``). The AI service layer talks
to the executor through a Protocol that lives in the executor
module itself (``SQLExecutor``), so the direction of imports is
deliberately "AI depends on the service interface, not on the
implementation". The schema registry (``backend.services.schema_registry``)
is allowed because it is pure data — a ``dict[str, frozenset[str]]``
with no database / SQLAlchemy dependency.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

AI_DIR = PROJECT_ROOT / "backend" / "ai"

# Forbidden web-framework imports. Keep this list narrow — only
# libraries the rest of the codebase actually uses.
FORBIDDEN_MODULES = frozenset({"fastapi", "starlette", "fastapi.testclient"})

# Also forbid SQLAlchemy / DB modules leaking into the AI layer
# (Phase 5 ships no AI service that touches the database).
FORBIDDEN_DATA_MODULES = frozenset(
    {"sqlalchemy", "backend.database", "backend.models"}
)

# And the SDK / provider-specific imports. Services must go
# through ``AIProvider``, never import an SDK directly.
FORBIDDEN_SDK_MODULES = frozenset(
    {
        "google",
        "openai",
        "anthropic",
        "groq",
    }
)

# Phase 6: the AI layer is allowed to import the schema allowlist
# (pure data) but NOT the database-touching executor / query
# service. The interface (``SQLExecutor``) is re-exported by the
# executor module — but the AI layer must not depend on the
# concrete implementation. We enforce this by forbidding the
# full module path of the implementation modules.
FORBIDDEN_AI_SERVICE_MODULES = frozenset(
    {
        "backend.services.sql_executor",
        "backend.services.ai_query_service",
    }
)

ALL_FORBIDDEN = (
    FORBIDDEN_MODULES | FORBIDDEN_DATA_MODULES | FORBIDDEN_SDK_MODULES
)


def _ai_modules() -> list[Path]:
    """Yield every ``.py`` file under ``backend/ai/`` (recursively)."""
    return sorted(
        p for p in AI_DIR.rglob("*.py") if p.name != "__pycache__"
    )


def _imports_in(path: Path) -> set[str]:
    """Return the set of top-level module names imported by ``path``.

    Also returns a parallel set of *full* dotted paths for any
    ``from backend... import ...`` statement. The top-level set
    is used for the broad forbidden-modules check; the full-path
    set is used for the Phase 6 service-module check.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    top: set[str] = set()
    full: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top.add(alias.name.split(".")[0])
                full.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue  # relative import — module name is empty
            top.add(node.module.split(".")[0])
            full.add(node.module)
    return top, full


# The provider module is *expected* to import the SDK it
# wraps. We still forbid the others there too.
PROVIDER_FILES = {
    (AI_DIR / "providers" / "gemini.py").resolve(),
}


def _expected_sdk_for(path: Path) -> set[str]:
    """The set of SDK names a file is allowed to import."""
    if path.resolve() in PROVIDER_FILES:
        return {"google", "google.genai"}
    return set()


@pytest.mark.parametrize("path", _ai_modules(), ids=lambda p: p.name)
def test_ai_module_has_no_forbidden_imports(path: Path) -> None:
    """No file in ``backend/ai/`` may import a web framework, the
    database, or an LLM SDK (except the file wrapping that SDK)."""
    top, _ = _imports_in(path)
    leaked = top & ALL_FORBIDDEN - _expected_sdk_for(path)
    assert not leaked, (
        f"{path.relative_to(PROJECT_ROOT)} imports forbidden modules "
        f"{sorted(leaked)}; the AI layer must remain "
        f"web-framework-, database-, and SDK-independent"
    )


@pytest.mark.parametrize("path", _ai_modules(), ids=lambda p: p.name)
def test_ai_module_does_not_import_db_services(path: Path) -> None:
    """Phase 6: the AI layer must not import the database-touching
    service modules. The schema allowlist is the only allowed
    ``backend.services`` import."""
    _, full = _imports_in(path)
    leaked = full & FORBIDDEN_AI_SERVICE_MODULES
    assert not leaked, (
        f"{path.relative_to(PROJECT_ROOT)} imports database-touching "
        f"service modules {sorted(leaked)}; the AI service layer "
        f"depends on the SQLExecutor protocol only."
    )


# ---------------------------------------------------------------------
# Public surface — anyone outside the AI layer should import
# only from ``backend.ai`` and the subpackages documented in
# ``backend/ai/__init__.py``.
# ---------------------------------------------------------------------


def test_ai_package_exports_public_surface() -> None:
    """The public symbols are re-exported from ``backend.ai``."""
    from backend import ai

    expected = {
        # Phase 5
        "AIProvider",
        "GeminiProvider",
        "get_provider",
        "reset_provider_cache",
        "ChatService",
        "PromptService",
        "ChatMessage",
        "ChatRequest",
        "ChatResponse",
        "ChatRole",
        "AIProviderError",
        "AIConfigurationError",
        "AIRequestError",
        "AIRateLimitError",
        "AITimeoutError",
        "AIResponseError",
        "UnsupportedProviderError",
        "PromptNotFoundError",
        # Phase 6 — investigation engine
        "IntentService",
        "SQLGenerationService",
        "SQLValidationService",
        "InvestigationService",
        "Intent",
        "IntentClassification",
        "GeneratedSQL",
        "ValidatedSQL",
        "EvidenceItem",
        "ExplanationBlock",
        "InvestigationResponse",
        "OperationType",
        "InvestigationError",
        "UnknownIntent",
        "PromptError",
        "ProviderFailure",
        "UnsafeSQL",
        "ValidationFailure",
        "ExecutionFailure",
    }
    missing = expected - set(dir(ai))
    assert not missing, f"backend.ai is missing public symbols: {missing}"


def test_ai_provider_is_abstract() -> None:
    """The ABC contract is preserved — the type is uninstantiable."""
    import abc

    from backend.ai.providers.base import AIProvider

    assert issubclass(AIProvider, abc.ABC)
    with pytest.raises(TypeError):
        AIProvider(api_key="k", model="m", timeout=1, max_retries=0)
