"""
Service-layer independence tests.

The Gemini AI provider (Phase 6+) will instantiate services directly,
with no FastAPI request in scope. If a service module ever imports
``fastapi`` or ``starlette`` — even for typing — that import will
break the AI provider at runtime.

These tests catch that at the source level: every module under
``backend/services/`` is loaded and its source code is scanned for
forbidden imports.

The check is purely textual, not behavioural — it would not catch a
service that, say, uses ``requests`` to make HTTP calls. But it
catches the two most likely regressions:

  * ``from fastapi import ...``
  * ``import fastapi``
  * ``from starlette import ...``
  * ``import starlette``
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.base import BaseService  # noqa: E402

SERVICES_DIR = PROJECT_ROOT / "backend" / "services"

# Anything under this set means the service layer has leaked a web-
# framework dependency. Keep this list small — only the libraries
# the codebase actually uses.
FORBIDDEN_MODULES = frozenset({"fastapi", "starlette", "fastapi.testclient"})


def _service_modules() -> list[Path]:
    """Yield every ``.py`` file under ``backend/services/``."""
    return sorted(p for p in SERVICES_DIR.rglob("*.py") if p.name != "__pycache__")


def _imports_in(path: Path) -> set[str]:
    """Return the set of top-level module names imported by ``path``.

    Walks the AST rather than the live module so we catch the import
    even if the surrounding code path is not exercised at test time.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue  # relative import — module name is empty
            names.add(node.module.split(".")[0])
    return names


# ---------------------------------------------------------------------
# Static checks
# ---------------------------------------------------------------------


@pytest.mark.parametrize("path", _service_modules(), ids=lambda p: p.name)
def test_service_module_has_no_web_framework_imports(path: Path) -> None:
    """No service module may import fastapi / starlette."""
    imported = _imports_in(path)
    leaked = imported & FORBIDDEN_MODULES
    assert not leaked, (
        f"{path.relative_to(PROJECT_ROOT)} imports forbidden modules "
        f"{sorted(leaked)}; the service layer must be web-framework-agnostic"
    )


# ---------------------------------------------------------------------
# Behavioural checks
# ---------------------------------------------------------------------


class TestBaseServiceContract:
    """The BaseService contract must hold for any concrete service."""

    def test_base_is_abstract(self):
        """Cannot instantiate BaseService directly — ABC guard."""
        import abc

        assert issubclass(BaseService, abc.ABC)

    def test_case_service_is_a_base_service(self):
        from backend.services import CaseService

        assert issubclass(CaseService, BaseService)

    def test_base_exposes_session_property(self):
        """BaseService must surface the bound session read-only."""
        from unittest.mock import MagicMock

        class _Concrete(BaseService):
            pass

        session = MagicMock(name="Session")
        svc = _Concrete(session)
        assert svc.session is session

    def test_concrete_service_can_be_built_with_a_session(self):
        """The Gemini AI provider will do exactly this — instantiate
        the service with a session it obtained itself."""
        from unittest.mock import MagicMock

        from backend.services import CaseService

        session = MagicMock(name="Session")
        service = CaseService(session)
        assert service.session is session

    def test_constructor_signature_is_stable(self):
        """A single positional ``session`` argument is the contract.
        Changing it is a breaking change for AI providers and tests."""
        from unittest.mock import MagicMock

        from backend.services import CaseService

        session = MagicMock(name="Session")
        # Must not require any additional arguments.
        CaseService(session)  # no exception


# ---------------------------------------------------------------------
# AI-friendly method surface
# ---------------------------------------------------------------------


class TestCaseServiceIsAIReady:
    """Phase 6+ will reuse these methods to build LLM context."""

    def test_list_cases_signature(self):
        from backend.services import CaseFilters, CaseService, CaseSort

        # All parameters are keyword-argument friendly (no positional
        # service-internal state needed).
        assert callable(CaseService.list_cases)

        import inspect

        sig = inspect.signature(CaseService.list_cases)
        params = list(sig.parameters)
        assert params[:4] == ["self", "filters", "page", "page_size"]
        assert "sort" in params

    def test_get_case_detail_signature(self):
        from backend.services import CaseService

        import inspect

        sig = inspect.signature(CaseService.get_case_detail)
        params = list(sig.parameters)
        assert params == ["self", "case_id"]

    def test_get_case_summary_signature(self):
        from backend.services import CaseService

        import inspect

        sig = inspect.signature(CaseService.get_case_summary)
        params = list(sig.parameters)
        assert params == ["self", "case_id"]

    def test_count_cases_signature(self):
        from backend.services import CaseService

        import inspect

        sig = inspect.signature(CaseService.count_cases)
        params = list(sig.parameters)
        assert params == ["self", "filters"]

    def test_summary_method_returns_orm_object(self):
        """``get_case_summary`` must return an ORM object so AI code
        can read any column without re-querying."""
        from unittest.mock import MagicMock

        from backend.services import CaseService

        case = MagicMock(name="CaseMaster")
        session = MagicMock(name="Session")
        result = MagicMock()
        result.scalar_one_or_none.return_value = case
        session.execute.return_value = result

        out = CaseService(session).get_case_summary(1)
        assert out is case
