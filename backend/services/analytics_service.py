"""
Service layer — analytics (aggregate / dashboard) reads.

  - :class:`AnalyticsService`    : all aggregations over :class:`CaseMaster`
  - :class:`DistrictRef`         : district name OR id filter
  - :class:`SummaryCounts`       : the 6 dashboard headline numbers
  - :class:`MonthlyTrend`        : one month bucket
  - :class:`CategoryCount`       : one row in a distribution

Every public method is a single ``select()`` round-trip — no raw SQL,
no N+1.

  * All distributions use ``func.count().group_by()``.
  * The recent-cases endpoint reuses the case-list eager-load
    pattern (``selectinload``) so child relationships do not trigger
    per-row queries.
  * The ``DistrictRef`` resolver mirrors the pattern in
    :class:`CaseService` — an unknown name resolves to a sentinel
    that short-circuits the call to an empty result (200, never 404).

The service is **FastAPI-independent**: only SQLAlchemy + ORM model
imports. The Gemini AI provider (Phase 6+) will instantiate it
directly with a session it obtained itself.

**Convictions / acquittals.** The KSP schema has no verdict table.
``get_summary`` returns ``0`` for these fields; the Pydantic
``DashboardSummaryOut`` documents the placeholder semantics so the
API surface is stable for clients and the AI provider.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session, selectinload

from backend.models.case import CaseMaster
from backend.models.geography import District
from backend.models.organisation import Unit
from backend.models.taxonomy import (
    CaseStatusMaster,
    CrimeHead,
)
from backend.services.base import BaseService

# ---------------------------------------------------------------------
# Public dataclasses — inputs and outputs of the analytics layer.
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class DistrictRef:
    """A district filter. Either a name or an id; id wins when both
    are given. An unknown name is a "no match" — the service returns
    empty results, never raises."""

    name: str | None = None
    district_id: int | None = None


@dataclass(frozen=True)
class SummaryCounts:
    """The six dashboard headline numbers."""

    total_cases: int
    open_cases: int
    closed_cases: int
    charge_sheet_filed: int
    convictions: int      # always 0 for now
    acquittals: int       # always 0 for now


@dataclass(frozen=True)
class MonthlyTrend:
    year: int
    month: int            # 1..12
    case_count: int


@dataclass(frozen=True)
class CategoryCount:
    """One row in a distribution (status / crime head / district)."""

    key: int | None       # lookup id, None when the FK is null
    label: str
    case_count: int


# CaseStatusMaster has five rows (see seed). The summary aggregates
# bucket them into three headline numbers and one chargesheet total.
# We map by *name* so the service is robust to id reordering.
_STATUS_OPEN_NAMES = frozenset({"Open", "Under Investigation"})
_STATUS_CLOSED_NAMES = frozenset({"Closed"})

# Lookup id -> display label for the status fallback path (when a
# case has a CaseStatusID that no longer exists in the master).
_STATUS_FALLBACK_LABEL = "Unknown"

# Lookup id -> display label for the crime-head fallback path.
_CRIME_HEAD_FALLBACK_LABEL = "Uncategorised"

# Lookup id -> display label for the district fallback path.
_DISTRICT_FALLBACK_LABEL = "Unassigned"


# ---------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------


class AnalyticsService(BaseService):
    """All dashboard / analytics reads.

    A fresh instance is created per request and takes the
    request-scoped session as a constructor argument — no globals,
    no hidden state.

    Inherits from :class:`BaseService`, which guarantees a stable
    constructor signature ``(session: Session)``. The Gemini AI
    provider will instantiate this service with the same argument
    list the FastAPI dependency-injection system uses.
    """

    # -----------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------

    def get_summary(
        self, district: DistrictRef | None = None
    ) -> SummaryCounts:
        """Return the six headline counts.

        Implementation:
          1. Resolve the district filter to an id (one tiny query, only
             when a name is given).
          2. One ``select(CaseStatusID, func.count()).group_by()`` round
             trip, with an optional Unit join for the district filter.
          3. Map the five status buckets in Python; resolve
             ``Open``/``Under Investigation`` -> ``open_cases`` and
             ``Closed`` -> ``closed_cases``. The chargesheet total is
             the ``Charge Sheeted`` bucket.
        """
        district_id = self._resolve_district_id(district)

        # 1. count by status (one query, joined to Unit when filtered)
        stmt = select(
            CaseMaster.CaseStatusID,
            func.count().label("cnt"),
        )
        stmt = self._apply_district_join(stmt, district_id)
        stmt = stmt.group_by(CaseMaster.CaseStatusID)

        rows = self._session.execute(stmt).all()
        # Build a {status_id: count} map. status_id may be None (no row).
        by_id: dict[int | None, int] = {}
        for sid, cnt in rows:
            by_id[sid] = int(cnt or 0)

        # 2. resolve the names in a single lookup query
        name_by_id: dict[int, str] = {}
        if by_id:
            ids = [sid for sid in by_id.keys() if sid is not None]
            if ids:
                name_rows = self._session.execute(
                    select(CaseStatusMaster.CaseStatusID,
                           CaseStatusMaster.CaseStatusName).where(
                        CaseStatusMaster.CaseStatusID.in_(ids)
                    )
                ).all()
                name_by_id = {sid: name for sid, name in name_rows}

        # 3. bucket the counts
        open_cases = 0
        closed_cases = 0
        charge_sheet_filed = 0
        for sid, cnt in by_id.items():
            if sid is None:
                continue
            name = name_by_id.get(sid, _STATUS_FALLBACK_LABEL)
            if name in _STATUS_OPEN_NAMES:
                open_cases += cnt
            elif name in _STATUS_CLOSED_NAMES:
                closed_cases += cnt
            elif name == "Charge Sheeted":
                charge_sheet_filed += cnt

        total_cases = sum(by_id.values())

        # Convictions and acquittals: not tracked in the current schema.
        return SummaryCounts(
            total_cases=total_cases,
            open_cases=open_cases,
            closed_cases=closed_cases,
            charge_sheet_filed=charge_sheet_filed,
            convictions=0,
            acquittals=0,
        )

    # -----------------------------------------------------------------
    # Monthly trends
    # -----------------------------------------------------------------

    def get_monthly_trends(
        self,
        year: int,
        district: DistrictRef | None = None,
    ) -> list[MonthlyTrend]:
        """Return the 12 monthly case counts for ``year``.

        Always returns 12 entries (Jan..Dec). Months with no cases
        are returned as ``case_count=0`` so the chart never has gaps.
        """
        district_id = self._resolve_district_id(district)

        # One group-by query: year, month -> count.
        stmt = select(
            extract("year", CaseMaster.CrimeRegisteredDate).label("yr"),
            extract("month", CaseMaster.CrimeRegisteredDate).label("mo"),
            func.count().label("cnt"),
        )
        stmt = self._apply_district_join(stmt, district_id)
        stmt = stmt.where(
            extract("year", CaseMaster.CrimeRegisteredDate) == year
        )
        stmt = stmt.group_by("yr", "mo")

        rows = self._session.execute(stmt).all()

        # Index results by month, then zero-fill.
        count_by_month: dict[int, int] = {
            int(mo): int(cnt) for _, mo, cnt in rows if mo is not None
        }
        return [
            MonthlyTrend(year=year, month=m, case_count=count_by_month.get(m, 0))
            for m in range(1, 13)
        ]

    # -----------------------------------------------------------------
    # Distributions
    # -----------------------------------------------------------------

    def get_crime_head_distribution(
        self, district: DistrictRef | None = None
    ) -> list[CategoryCount]:
        """Return case counts grouped by Crime Head."""
        district_id = self._resolve_district_id(district)

        stmt = select(
            CaseMaster.CrimeMajorHeadID.label("head_id"),
            func.count().label("cnt"),
        )
        stmt = self._apply_district_join(stmt, district_id)
        stmt = stmt.group_by(CaseMaster.CrimeMajorHeadID)

        rows = self._session.execute(stmt).all()
        head_ids = [h for h, _ in rows if h is not None]

        # Resolve the labels in one follow-up query so the group-by
        # above stays simple. An id that has no row in CrimeHead maps
        # to a fallback label.
        name_by_id: dict[int, str] = {}
        if head_ids:
            name_rows = self._session.execute(
                select(CrimeHead.CrimeHeadID, CrimeHead.CrimeGroupName).where(
                    CrimeHead.CrimeHeadID.in_(head_ids)
                )
            ).all()
            name_by_id = {hid: name for hid, name in name_rows}

        return [
            CategoryCount(
                key=head_id,
                label=name_by_id.get(head_id, _CRIME_HEAD_FALLBACK_LABEL)
                if head_id is not None
                else _CRIME_HEAD_FALLBACK_LABEL,
                case_count=int(cnt or 0),
            )
            for head_id, cnt in rows
        ]

    def get_status_distribution(self) -> list[CategoryCount]:
        """Return case counts grouped by Case Status."""
        stmt = select(
            CaseMaster.CaseStatusID.label("status_id"),
            func.count().label("cnt"),
        ).group_by(CaseMaster.CaseStatusID)
        rows = self._session.execute(stmt).all()

        status_ids = [s for s, _ in rows if s is not None]
        name_by_id: dict[int, str] = {}
        if status_ids:
            name_rows = self._session.execute(
                select(
                    CaseStatusMaster.CaseStatusID, CaseStatusMaster.CaseStatusName
                ).where(CaseStatusMaster.CaseStatusID.in_(status_ids))
            ).all()
            name_by_id = {sid: name for sid, name in name_rows}

        return [
            CategoryCount(
                key=status_id,
                label=name_by_id.get(status_id, _STATUS_FALLBACK_LABEL)
                if status_id is not None
                else _STATUS_FALLBACK_LABEL,
                case_count=int(cnt or 0),
            )
            for status_id, cnt in rows
        ]

    def get_district_distribution(self) -> list[CategoryCount]:
        """Return case counts grouped by District.

        Joins ``CaseMaster`` -> ``Unit`` -> ``District`` so a case
        with no Unit row is bucketed under a fallback label.
        """
        stmt = (
            select(
                District.DistrictID.label("district_id"),
                District.DistrictName.label("district_name"),
                func.count(CaseMaster.CaseMasterID).label("cnt"),
            )
            .select_from(CaseMaster)
            .join(Unit, Unit.UnitID == CaseMaster.PoliceStationID, isouter=True)
            .join(
                District,
                District.DistrictID == Unit.DistrictID,
                isouter=True,
            )
            .group_by(District.DistrictID, District.DistrictName)
        )
        rows = self._session.execute(stmt).all()
        return [
            CategoryCount(
                key=did,
                label=name if name is not None else _DISTRICT_FALLBACK_LABEL,
                case_count=int(cnt or 0),
            )
            for did, name, cnt in rows
        ]

    # -----------------------------------------------------------------
    # Recent cases (paginated, no district filter — pure recency)
    # -----------------------------------------------------------------

    def get_recent_cases(
        self, page: int = 1, page_size: int = 10
    ) -> tuple[Sequence[CaseMaster], int]:
        """Return the latest registered cases, paginated.

        Eager-loads the same relationships the case-list endpoint
        uses so a downstream Pydantic conversion does not trigger
        N+1. The count is a separate query, unaffected by
        ``limit``/``offset``.
        """
        # 1. count
        count_stmt = select(func.count()).select_from(CaseMaster)
        total = int(self._session.execute(count_stmt).scalar_one() or 0)

        # 2. page
        stmt = select(CaseMaster).options(
            selectinload(CaseMaster.case_status),
            selectinload(CaseMaster.case_category),
            selectinload(CaseMaster.gravity),
            selectinload(CaseMaster.crime_major_head),
            selectinload(CaseMaster.crime_minor_head),
            selectinload(CaseMaster.police_station).selectinload(Unit.district),
        )
        stmt = stmt.order_by(
            CaseMaster.CrimeRegisteredDate.desc(),
            CaseMaster.CaseMasterID.desc(),
        )
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)

        rows = self._session.execute(stmt).scalars().all()
        return rows, total

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------

    def _resolve_district_id(
        self, ref: DistrictRef | None
    ) -> int | None | str:
        """Return the resolved district id, ``None`` (no filter), or
        the sentinel ``"__no_match__"`` (unknown name — caller
        short-circuits to empty).

        Mirrors the resolution pattern in :class:`CaseService` so the
        two services stay symmetric.
        """
        if ref is None:
            return None
        if ref.district_id is not None:
            return ref.district_id
        if ref.name:
            row = self._session.execute(
                select(District.DistrictID).where(
                    func.lower(District.DistrictName) == ref.name.strip().lower()
                )
            ).first()
            if row is None:
                return "__no_match__"
            return row[0]
        return None

    @staticmethod
    def _apply_district_join(stmt, district_id):
        """Add the Unit join + district filter, or short-circuit on
        the no-match sentinel. Idempotent — safe to call once per
        query."""
        if district_id == "__no_match__":
            return stmt.where(False)  # always-false predicate
        if district_id is None:
            return stmt
        return (
            stmt.join(Unit, Unit.UnitID == CaseMaster.PoliceStationID)
            .where(Unit.DistrictID == district_id)
        )
