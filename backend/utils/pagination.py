"""
Pagination math — kept here so the service layer doesn't have to know it
and so it can be unit-tested in isolation.
"""
from __future__ import annotations

from math import ceil

from backend.schemas.common import PaginationMeta


def calculate_pagination(
    page: int, page_size: int, total: int
) -> PaginationMeta:
    """Build a :class:`PaginationMeta` from raw counts.

    Rules:

      * ``page`` is 1-based.
      * ``total_pages`` is 0 when ``total == 0``, otherwise ``ceil(total/page_size)``.
      * ``has_next`` is true when there is at least one row after this page.
      * ``has_prev`` is true when ``page > 1``.
    """
    if page < 1:
        raise ValueError("page must be >= 1")
    if page_size < 1:
        raise ValueError("page_size must be >= 1")
    if total < 0:
        raise ValueError("total must be >= 0")

    total_pages = ceil(total / page_size) if total else 0
    return PaginationMeta(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )
