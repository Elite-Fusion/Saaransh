"""
Service layer — Case (FIR) read operations.

  - :class:`CaseService`      : list + detail queries, all via the ORM
  - :class:`CaseFilters`      : validated filter set consumed by the service
  - :class:`CaseSort`         : whitelisted sort field + direction
  - :class:`CaseNotFoundError`: raised when an id has no matching case

All queries are built with ``select()`` — no raw SQL.

The service is **FastAPI-independent**: it only imports SQLAlchemy and
the ORM models. The Gemini AI provider (Phase 6+) will reuse these
methods to fetch case data for the LLM context window.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.models.case import ActSectionAssociation, CaseMaster
from backend.models.geography import District
from backend.models.organisation import Unit
from backend.models.taxonomy import (
    CaseStatusMaster,
    CrimeHead,
    CrimeSubHead,
)
from backend.services.base import BaseService


# ---------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------


class CaseNotFoundError(Exception):
    """Raised by :meth:`CaseService.get_case_detail` when the id is unknown."""

    def __init__(self, case_id: int) -> None:
        super().__init__(f"Case {case_id} not found")
        self.case_id = case_id


# Sort whitelist — keeps clients from sorting on arbitrary columns.
ALLOWED_SORT_FIELDS: frozenset[str] = frozenset(
    {
        "crime_no",
        "crime_registered_date",
        "case_status",
        "created_at",
        "case_id",
    }
)

# Map whitelist key -> ORM column. The service translates the public
# name into the column at runtime so we never touch user input directly.
_SORT_COLUMN_MAP = {
    "crime_no": CaseMaster.CrimeNo,
    "crime_registered_date": CaseMaster.CrimeRegisteredDate,
    "case_status": CaseMaster.CaseStatusID,
    "created_at": CaseMaster.created_at,
    "case_id": CaseMaster.CaseMasterID,
}


@dataclass(frozen=True)
class CaseFilters:
    """All filter values that the service understands.

    ``*_id`` fields always win when both the id and the name are given.
    A name that does not match a known lookup row is treated as
    'no match' — the list endpoint simply returns zero rows.
    """

    fir_number: str | None = None

    district: str | None = None
    district_id: int | None = None

    police_station: str | None = None
    police_station_id: int | None = None

    crime_head: str | None = None
    crime_head_id: int | None = None

    crime_sub_head: str | None = None
    crime_sub_head_id: int | None = None

    status: str | None = None
    status_id: int | None = None

    date_from: date | None = None
    date_to: date | None = None


@dataclass(frozen=True)
class CaseSort:
    field: str
    order: str  # "asc" | "desc"


# ---------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------


class CaseService(BaseService):
    """All case-related reads.

    A fresh instance is created per request and takes the request-scoped
    session as a constructor argument — no globals, no hidden state.

    Inherits from :class:`BaseService`, which guarantees a stable
    constructor signature ``(session: Session)``. The Gemini AI
    provider will instantiate services with the same argument list
    the FastAPI dependency-injection system uses.
    """

    # -- public API ----------------------------------------------------

    def list_cases(
        self,
        filters: CaseFilters,
        page: int,
        page_size: int,
        sort: CaseSort,
    ) -> tuple[Sequence[CaseMaster], int]:
        """Return ``(rows, total)`` for the given filter / sort / page.

        Implementation:

          1. Resolve name-based filters to ids (one tiny query each, only
             when the caller didn't already pass an id).
          2. Build the main ``select()`` with the resolved filters and
             ``selectinload`` the relationships that the summary schema
             needs.
          3. Count with a separate ``select(func.count())`` so the count
             is unaffected by ``limit`` / ``offset``.
          4. Apply the whitelisted sort + pagination, then execute.
        """
        # Resolve names -> ids once, before building the main query.
        resolved = self._resolve_filter_ids(filters)

        # ---- 1. count ------------------------------------------------
        count_stmt = select(func.count()).select_from(CaseMaster)
        count_stmt = self._apply_filters(count_stmt, filters, resolved)
        total = int(self._session.execute(count_stmt).scalar_one() or 0)

        # ---- 2. page -------------------------------------------------
        stmt = select(CaseMaster).options(
            selectinload(CaseMaster.case_status),
            selectinload(CaseMaster.case_category),
            selectinload(CaseMaster.gravity),
            selectinload(CaseMaster.crime_major_head),
            selectinload(CaseMaster.crime_minor_head),
            selectinload(CaseMaster.police_station).selectinload(Unit.district),
        )
        stmt = self._apply_filters(stmt, filters, resolved)
        stmt = self._apply_sort(stmt, sort)
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)

        rows = self._session.execute(stmt).scalars().all()
        return rows, total

    def get_case_detail(self, case_id: int) -> CaseMaster:
        """Return the case with all child collections eagerly loaded.

        Raises :class:`CaseNotFoundError` if no such case exists.
        """
        stmt = (
            select(CaseMaster)
            .where(CaseMaster.CaseMasterID == case_id)
            .options(
                # 1-to-1 named relationships used by the detail schema
                selectinload(CaseMaster.case_status),
                selectinload(CaseMaster.case_category),
                selectinload(CaseMaster.gravity),
                selectinload(CaseMaster.crime_major_head),
                selectinload(CaseMaster.crime_minor_head),
                selectinload(CaseMaster.court),
                selectinload(CaseMaster.police_station).selectinload(
                    Unit.district
                ),
                selectinload(CaseMaster.investigating_officer),
                # 1-to-many children
                selectinload(CaseMaster.complainants),
                selectinload(CaseMaster.victims),
                selectinload(CaseMaster.accused),
                selectinload(CaseMaster.evidence),
                selectinload(CaseMaster.recovered_items),
                selectinload(CaseMaster.act_sections).selectinload(
                    ActSectionAssociation.act
                ),
                selectinload(CaseMaster.chargesheet),
            )
        )
        case = self._session.execute(stmt).scalar_one_or_none()
        if case is None:
            raise CaseNotFoundError(case_id)
        return case

    def get_case_summary(self, case_id: int) -> CaseMaster:
        """Return one case row with **no child collections loaded**.

        Designed for the Gemini AI provider: small payloads are
        cheaper to embed and stay within the LLM context window.
        Only the case's own columns are returned — none of the
        relationships used by the detail schema are loaded.

        Raises :class:`CaseNotFoundError` if no such case exists.
        """
        stmt = select(CaseMaster).where(CaseMaster.CaseMasterID == case_id)
        case = self._session.execute(stmt).scalar_one_or_none()
        if case is None:
            raise CaseNotFoundError(case_id)
        return case

    def count_cases(self, filters: CaseFilters | None = None) -> int:
        """Return the total number of cases that match ``filters``.

        A read-only aggregate useful for AI features that need to
        decide "are there enough results to summarise?" without
        materialising the rows.

        ``filters`` is optional; when ``None`` the count is unfiltered.
        """
        # Build the same WHERE clauses the list endpoint would build.
        if filters is None:
            filters = CaseFilters()
        resolved = self._resolve_filter_ids(filters)
        count_stmt = select(func.count()).select_from(CaseMaster)
        count_stmt = self._apply_filters(count_stmt, filters, resolved)
        return int(self._session.execute(count_stmt).scalar_one() or 0)

    # -- helpers -------------------------------------------------------

    def _resolve_filter_ids(self, filters: CaseFilters) -> dict[str, int]:
        """Resolve name-based filters to ids, leaving id-based filters
        untouched. Returns a dict with the resolved ids; an empty dict
        means 'no filters that needed resolution'.

        If a name does not match a known row, returns a dict with
        ``__no_match__ = 1`` and the caller short-circuits to 0 rows.
        """
        resolved: dict[str, int] = {}

        # district
        if filters.district_id is None and filters.district:
            row = self._session.execute(
                select(District.DistrictID).where(
                    func.lower(District.DistrictName)
                    == filters.district.strip().lower()
                )
            ).first()
            if row is None:
                return {"__no_match__": 1}
            resolved["district_id"] = row[0]
        elif filters.district_id is not None:
            resolved["district_id"] = filters.district_id

        # police station
        if filters.police_station_id is None and filters.police_station:
            row = self._session.execute(
                select(Unit.UnitID).where(
                    func.lower(Unit.UnitName)
                    == filters.police_station.strip().lower()
                )
            ).first()
            if row is None:
                return {"__no_match__": 1}
            resolved["police_station_id"] = row[0]
        elif filters.police_station_id is not None:
            resolved["police_station_id"] = filters.police_station_id

        # crime head (major)
        if filters.crime_head_id is None and filters.crime_head:
            row = self._session.execute(
                select(CrimeHead.CrimeHeadID).where(
                    func.lower(CrimeHead.CrimeGroupName)
                    == filters.crime_head.strip().lower()
                )
            ).first()
            if row is None:
                return {"__no_match__": 1}
            resolved["crime_head_id"] = row[0]
        elif filters.crime_head_id is not None:
            resolved["crime_head_id"] = filters.crime_head_id

        # crime sub head (minor)
        if filters.crime_sub_head_id is None and filters.crime_sub_head:
            row = self._session.execute(
                select(CrimeSubHead.CrimeSubHeadID).where(
                    func.lower(CrimeSubHead.CrimeHeadName)
                    == filters.crime_sub_head.strip().lower()
                )
            ).first()
            if row is None:
                return {"__no_match__": 1}
            resolved["crime_sub_head_id"] = row[0]
        elif filters.crime_sub_head_id is not None:
            resolved["crime_sub_head_id"] = filters.crime_sub_head_id

        # status
        if filters.status_id is None and filters.status:
            row = self._session.execute(
                select(CaseStatusMaster.CaseStatusID).where(
                    func.lower(CaseStatusMaster.CaseStatusName)
                    == filters.status.strip().lower()
                )
            ).first()
            if row is None:
                return {"__no_match__": 1}
            resolved["status_id"] = row[0]
        elif filters.status_id is not None:
            resolved["status_id"] = filters.status_id

        return resolved

    @staticmethod
    def _apply_filters(stmt, filters: CaseFilters, resolved: dict[str, int]):
        """Apply WHERE clauses for every active filter."""
        # Short-circuit: a name resolved to 'no match' yields 0 rows.
        if resolved.get("__no_match__"):
            return stmt.where(False)  # always-false predicate

        if filters.fir_number:
            stmt = stmt.where(CaseMaster.CrimeNo == filters.fir_number)

        if "district_id" in resolved:
            # police_station is the join bridge; filter on its district.
            stmt = stmt.join(
                Unit, Unit.UnitID == CaseMaster.PoliceStationID
            ).where(Unit.DistrictID == resolved["district_id"])
        elif "police_station_id" in resolved:
            stmt = stmt.where(
                CaseMaster.PoliceStationID == resolved["police_station_id"]
            )

        if "crime_head_id" in resolved:
            stmt = stmt.where(
                CaseMaster.CrimeMajorHeadID == resolved["crime_head_id"]
            )
        if "crime_sub_head_id" in resolved:
            stmt = stmt.where(
                CaseMaster.CrimeMinorHeadID == resolved["crime_sub_head_id"]
            )
        if "status_id" in resolved:
            stmt = stmt.where(
                CaseMaster.CaseStatusID == resolved["status_id"]
            )

        if filters.date_from is not None:
            stmt = stmt.where(
                CaseMaster.CrimeRegisteredDate >= filters.date_from
            )
        if filters.date_to is not None:
            stmt = stmt.where(
                CaseMaster.CrimeRegisteredDate <= filters.date_to
            )

        return stmt

    @staticmethod
    def _apply_sort(stmt, sort: CaseSort):
        column = _SORT_COLUMN_MAP.get(sort.field)
        if column is None:
            raise ValueError(f"Unknown sort field: {sort.field!r}")
        if sort.order == "desc":
            return stmt.order_by(column.desc())
        return stmt.order_by(column.asc())
