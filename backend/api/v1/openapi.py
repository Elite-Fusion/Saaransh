"""
OpenAPI metadata helpers.

Every route in :mod:`backend.api.v1` documents the same four kinds of
responses:

  * **200 / 2xx Success**       — payload examples
  * **400 Bad Request**         — invalid sort, malformed input from us
  * **404 Not Found**           — the resource does not exist
  * **422 Unprocessable Entity** — Pydantic validation failure
  * **Empty Results**           — a success that legitimately carries no rows

Defining these inline per route leads to drift. This module centralises
the pattern: a single ``standard_error_responses(...)`` call returns a
``responses`` dict that any route can ``**spread`` into its decorator.
Future routes get full documentation for free.

This file is the *only* place that knows the names of the example
constants in :mod:`backend.api.v1.examples`. Routes stay declarative.
"""
from __future__ import annotations

from typing import Any, Mapping

from fastapi import status
from pydantic import BaseModel

from backend.api.v1 import examples
from backend.schemas.common import ErrorDetail

__all__ = [
    "attach_examples",
    "code_samples",
    "standard_error_responses",
]


# ---------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------


def _json_examples(*pairs: tuple[str, dict[str, Any]]) -> dict[str, Any]:
    """Return the FastAPI ``content[media_type].examples`` payload from
    a sequence of ``(name, example_dict)`` pairs.

    Each input example must be a complete OpenAPI example object — the
    same shape used in :mod:`backend.api.v1.examples`:

        {"summary": "...", "description": "...", "value": {...}}

    The pairs are emitted in the order given so the Swagger dropdown
    matches the order we want consumers to read.
    """
    return {name: example for name, example in pairs}


def _validation_example() -> dict[str, Any]:
    """The 422 envelope FastAPI produces (a list of error items)."""
    return {"example": examples.EXAMPLE_VALIDATION_ERROR["value"]}


def _error_response(
    *,
    model: type[BaseModel],
    description: str,
    examples: Mapping[str, dict[str, Any]],
) -> dict[str, Any]:
    """Wrap an error response in the FastAPI ``responses[code]`` shape."""
    return {
        "model": model,
        "description": description,
        "content": {
            "application/json": {
                "examples": dict(examples),
            }
        },
    }


# ---------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------


def standard_error_responses(
    *,
    success_model: type[BaseModel] | None = None,
    success_examples: Mapping[str, dict[str, Any]] | None = None,
    success_description: str = "Successful response.",
    include_not_found: bool = True,
    not_found_examples: Mapping[str, dict[str, Any]] | None = None,
    not_found_description: str = "Resource not found.",
    include_bad_request: bool = True,
    bad_request_examples: Mapping[str, dict[str, Any]] | None = None,
    bad_request_description: str = "Invalid request parameters.",
    include_validation: bool = True,
    include_empty: bool = False,
    empty_example: dict[str, Any] | None = None,
) -> dict[int | str, dict[str, Any]]:
    """Build the standard ``responses=`` dict for a route decorator.

    Usage::

        @router.get(
            "/items",
            response_model=ItemListResponse,
            responses=standard_error_responses(
                success_model=ItemListResponse,
                success_examples={"success": examples.EXAMPLE_ITEMS_SUCCESS},
                not_found_examples={"missing": examples.EXAMPLE_NOT_FOUND},
                bad_request_examples={"invalid": examples.EXAMPLE_BAD_REQUEST},
                include_empty=True,
                empty_example=examples.EXAMPLE_ITEMS_EMPTY,
            ),
        )

    The returned dict can be ``**spread`` directly into ``responses=``.
    """
    responses: dict[int | str, dict[str, Any]] = {}

    # 2xx — success
    if success_model is not None and success_examples is not None:
        responses[status.HTTP_200_OK] = {
            "model": success_model,
            "description": success_description,
            "content": {
                "application/json": {
                    "examples": dict(success_examples),
                }
            },
        }

    # 4xx — bad request (invalid sort, malformed input from our code)
    if include_bad_request and bad_request_examples:
        responses[status.HTTP_400_BAD_REQUEST] = _error_response(
            model=ErrorDetail,
            description=bad_request_description,
            examples=bad_request_examples,
        )

    # 4xx — not found
    if include_not_found and not_found_examples:
        responses[status.HTTP_404_NOT_FOUND] = _error_response(
            model=ErrorDetail,
            description=not_found_description,
            examples=not_found_examples,
        )

    # 4xx — pydantic validation
    if include_validation:
        responses[status.HTTP_422_UNPROCESSABLE_ENTITY] = {
            "description": "Validation error (Pydantic).",
            "content": {"application/json": _validation_example()},
        }

    # 2xx — empty (some endpoints document a separate empty example)
    if include_empty and empty_example is not None:
        # Caller has already placed the empty example under success_examples
        # in most cases. This hook is here for symmetry / future use.
        pass

    return responses


def attach_examples(
    *,
    success: dict[str, dict[str, Any]] | None = None,
    bad_request: dict[str, dict[str, Any]] | None = None,
    not_found: dict[str, dict[str, Any]] | None = None,
    empty: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Group example dicts by category for direct use in ``responses=``.

    Most routes don't need this — :func:`standard_error_responses` is
    the higher-level wrapper. This lower-level helper is useful when a
    route has a non-standard shape (custom status codes, alternate
    media types, etc.) but still wants to organise its examples.
    """
    out: dict[str, Any] = {}
    if success:
        out["success"] = _json_examples(*success.items())
    if empty:
        out["empty"] = _json_examples(*empty.items())
    if bad_request:
        out["bad_request"] = _json_examples(*bad_request.items())
    if not_found:
        out["not_found"] = _json_examples(*not_found.items())
    return out


def code_samples(*samples: dict[str, str]) -> dict[str, list[dict[str, str]]]:
    """Build the ``openapi_extra['x-codeSamples']`` payload from a
    sequence of ``{"lang": "...", "source": "..."}`` dicts.

    ReDoc renders these as a "Try it" panel.
    """
    return {"x-codeSamples": list(samples)}
