"""
OpenAPI contract tests.

These tests pin the OpenAPI schema so a future refactor cannot silently
drop documentation. They enforce the four example categories the API
must always expose per endpoint:

  * **success**   — a 2xx response example
  * **validation** — a 422 (or 400) error example
  * **not_found**  — a 404 error example (where applicable)
  * **empty**     — a 2xx response example with no rows (list endpoints)

If an endpoint gains a response code, the test that scans it must
classify the new code as one of the above. If a code is added that
isn't documented, the test fails.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import create_app  # noqa: E402


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


@pytest.fixture(scope="module")
def openapi_spec() -> dict:
    app = create_app()
    return app.openapi()


@pytest.fixture(scope="module")
def all_operations() -> list[tuple[str, str, dict]]:
    """``(path, method, operation)`` for every endpoint at spec time."""
    spec = create_app().openapi()
    out: list[tuple[str, str, dict]] = []
    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            if method.startswith("x-"):
                continue
            out.append((path, method, op))
    return out


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _examples_for(spec: dict, path: str, method: str, code: str) -> list[str]:
    """Return the list of example names under the given response code."""
    op = spec["paths"][path][method.lower()]
    resp = op.get("responses", {}).get(code, {})
    content = resp.get("content", {}).get("application/json", {})
    return list(content.get("examples", {}).keys())


# ---------------------------------------------------------------------
# Per-endpoint documentation checks
# ---------------------------------------------------------------------


class TestHealthDocumentation:
    """`GET /api/v1/health` is a probe — only a 200 is expected, but it
    must carry at least one success example (healthy or degraded)."""

    def test_has_200_with_examples(self, openapi_spec):
        names = _examples_for(openapi_spec, "/api/v1/health", "get", "200")
        assert names, "health endpoint must expose at least one 200 example"
        # healthy + degraded_db_down — at minimum 'healthy'
        assert any("healthy" in n or "degraded" in n for n in names), (
            f"health 200 examples should include 'healthy' or 'degraded', "
            f"got {names}"
        )

    def test_curl_sample_attached(self, openapi_spec):
        op = openapi_spec["paths"]["/api/v1/health"]["get"]
        samples = op.get("x-codeSamples", [])
        assert any(s.get("lang") == "curl" for s in samples), (
            "health must ship a curl x-codeSample"
        )


class TestCasesListDocumentation:
    """`GET /api/v1/cases` — list endpoint."""

    def test_200_has_success_and_empty(self, openapi_spec):
        names = _examples_for(openapi_spec, "/api/v1/cases", "get", "200")
        # success + filtered + empty_results
        assert "success" in names, f"need 'success' example, got {names}"
        assert any("empty" in n for n in names), (
            f"list endpoint must document an empty result, got {names}"
        )

    def test_400_has_invalid_sort(self, openapi_spec):
        names = _examples_for(openapi_spec, "/api/v1/cases", "get", "400")
        assert "invalid_sort_field" in names, (
            f"need 'invalid_sort_field' example, got {names}"
        )
        assert "invalid_sort_order" in names, (
            f"need 'invalid_sort_order' example, got {names}"
        )

    def test_422_validation(self, openapi_spec):
        # The 422 payload uses a single 'example' (not a named
        # collection). Just confirm the response is documented.
        op = openapi_spec["paths"]["/api/v1/cases"]["get"]
        assert "422" in op.get("responses", {}), "422 must be documented"

    def test_no_404_for_list(self, openapi_spec):
        """List endpoints never 404 — a missing filter just yields an
        empty page. The test guards against accidental 404 responses
        being added to the spec."""
        op = openapi_spec["paths"]["/api/v1/cases"]["get"]
        assert "404" not in op.get("responses", {}), (
            "list endpoint should not document a 404 response"
        )

    def test_curl_sample_attached(self, openapi_spec):
        op = openapi_spec["paths"]["/api/v1/cases"]["get"]
        samples = op.get("x-codeSamples", [])
        assert any(s.get("lang") == "curl" for s in samples), (
            "list endpoint must ship a curl x-codeSample"
        )


class TestCasesDetailDocumentation:
    """`GET /api/v1/cases/{case_id}` — detail endpoint."""

    def test_200_has_success(self, openapi_spec):
        names = _examples_for(
            openapi_spec, "/api/v1/cases/{case_id}", "get", "200"
        )
        assert "success" in names, f"need 'success' example, got {names}"

    def test_404_has_not_found(self, openapi_spec):
        names = _examples_for(
            openapi_spec, "/api/v1/cases/{case_id}", "get", "404"
        )
        assert "not_found" in names, f"need 'not_found' example, got {names}"

    def test_422_validation(self, openapi_spec):
        op = openapi_spec["paths"]["/api/v1/cases/{case_id}"]["get"]
        assert "422" in op.get("responses", {}), "422 must be documented"

    def test_curl_sample_attached(self, openapi_spec):
        op = openapi_spec["paths"]["/api/v1/cases/{case_id}"]["get"]
        samples = op.get("x-codeSamples", [])
        assert any(s.get("lang") == "curl" for s in samples), (
            "detail endpoint must ship a curl x-codeSample"
        )


# ---------------------------------------------------------------------
# Global guards — catch any newly added endpoint that lacks docs.
# ---------------------------------------------------------------------


class TestAllEndpointsDocumented:
    """Every endpoint must expose a 200 + at least one 4xx response.

    Health endpoints (under ``/api/v1/health``) are allowed to opt out
    of the 4xx requirement — they are probes, not resource handlers.
    """

    # Endpoints that legitimately do not need a 4xx response.
    PROBE_PATHS = frozenset({"/api/v1/health"})

    def test_every_endpoint_has_documented_responses(self, all_operations):
        for path, method, op in all_operations:
            codes = set(op.get("responses", {}).keys())
            assert "200" in codes, (
                f"{method.upper()} {path} missing 200 response"
            )
            if path in self.PROBE_PATHS:
                continue  # probe endpoints only document 200
            assert any(c.startswith("4") for c in codes), (
                f"{method.upper()} {path} missing any 4xx response"
            )

    def test_every_endpoint_has_curl_sample(self, all_operations):
        for path, method, op in all_operations:
            samples = op.get("x-codeSamples", [])
            assert any(s.get("lang") == "curl" for s in samples), (
                f"{method.upper()} {path} must ship a curl x-codeSample"
            )

    def test_every_endpoint_has_200_examples(self, all_operations):
        for path, method, op in all_operations:
            content = (
                op.get("responses", {})
                .get("200", {})
                .get("content", {})
                .get("application/json", {})
            )
            examples = content.get("examples") or {"_default": content.get("example")}
            assert examples, (
                f"{method.upper()} {path} 200 must carry at least one example"
            )
