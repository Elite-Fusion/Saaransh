"""
Shared Pydantic models used by every API.

  - ``PaginationParams``  : input (query string) — page, page_size
  - ``PaginationMeta``    : output (response body) — total, has_next, …
  - ``SortOrder``         : ``asc`` or ``desc``
  - ``ErrorResponse`` / ``ErrorDetail`` : structured error envelope
  - ``PaginatedResponse`` : generic wrapper holding items + pagination
"""
from __future__ import annotations

from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

SortOrder = Literal["asc", "desc"]


class PaginationParams(BaseModel):
    """Input — bound from the query string by the route layer."""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=1, ge=1, description="1-based page number")
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page (max 100)",
    )


class PaginationMeta(BaseModel):
    """Output — describes the current page and the full result set."""

    total: int = Field(..., ge=0, description="Total matching rows")
    page: int = Field(..., ge=1, description="Current 1-based page number")
    page_size: int = Field(..., ge=1, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="True if a next page exists")
    has_prev: bool = Field(..., description="True if a previous page exists")


class ErrorDetail(BaseModel):
    """Body of a structured error."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable message")
    details: Any | None = Field(
        default=None,
        description="Optional structured context for the error",
    )


class ErrorResponse(BaseModel):
    """Envelope returned for every non-2xx response."""

    error: ErrorDetail


def make_paginated_response(
    items: list[T], meta: PaginationMeta
) -> dict[str, Any]:
    """Build a ``PaginatedResponse`` dict.

    Pydantic v2 supports ``Generic[T]`` model classes, but to keep the
    OpenAPI schema simple (one concrete shape, not one per resource
    type) we expose a small factory that returns the dict payload. The
    route layer wraps it in the response model of choice.
    """
    return {"items": items, "pagination": meta.model_dump()}


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated envelope. The route uses the explicit
    ``CaseListResponse`` alias so Swagger shows a concrete name.
    """

    items: list[T]
    pagination: PaginationMeta
