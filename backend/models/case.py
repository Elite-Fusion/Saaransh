"""
SQLAlchemy ORM models — Case Core group.

The heart of the database: CaseMaster and everything attached to it.
This is the FIR and its universe of complainant, victim, accused, charges,
arrest, chargesheet, evidence, and recovered items.

Tables:
  - CaseMaster
  - ComplainantDetails
  - Victim
  - Accused
  - ArrestSurrender
  - ActSectionAssociation
  - ChargesheetDetails
  - Evidence
  - RecoveredItems
"""
from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CHAR,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from backend.database.session import Base

if TYPE_CHECKING:
    from backend.models.ai import AuditLog
    from backend.models.organisation import Court, Employee, Unit
    from backend.models.taxonomy import (
        Act,
        CaseCategory,
        CaseStatusMaster,
        CrimeHead,
        CrimeSubHead,
        GravityOffence,
    )


class CaseMaster(Base):
    """An FIR (First Information Report) — the central entity."""

    __tablename__ = "CaseMaster"

    CaseMasterID: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    CrimeNo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    CaseNo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    CrimeRegisteredDate: Mapped[date] = mapped_column(Date, nullable=False)
    PolicePersonID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Employee.EmployeeID"), nullable=True
    )
    PoliceStationID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Unit.UnitID"), nullable=True
    )
    CaseCategoryID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("CaseCategory.CaseCategoryID"), nullable=True
    )
    GravityOffenceID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("GravityOffence.GravityOffenceID"), nullable=True
    )
    CrimeMajorHeadID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("CrimeHead.CrimeHeadID"), nullable=True
    )
    CrimeMinorHeadID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("CrimeSubHead.CrimeSubHeadID"), nullable=True
    )
    CaseStatusID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("CaseStatusMaster.CaseStatusID"), nullable=True
    )
    CourtID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Court.CourtID"), nullable=True
    )
    IncidentFromDate: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    IncidentToDate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    InfoReceivedPSDate: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    BriefFacts: Mapped[str | None] = mapped_column(Text, nullable=True)

    # AI extensions -----------------------------------------------------------
    mo_embedding: Mapped[list[float] | None] = mapped_column(
        Vector(384), nullable=True
    )
    is_series_crime: Mapped[bool | None] = mapped_column(
        Boolean, default=False, nullable=True
    )
    series_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=None, nullable=True
    )

    # Relationships ----------------------------------------------------------
    police_station: Mapped["Unit | None"] = relationship(  # noqa: F821
        "Unit", foreign_keys=[PoliceStationID]
    )
    investigating_officer: Mapped["Employee | None"] = relationship(  # noqa: F821
        "Employee", foreign_keys=[PolicePersonID]
    )
    court: Mapped["Court | None"] = relationship(  # noqa: F821
        "Court", foreign_keys=[CourtID]
    )
    case_category: Mapped["CaseCategory | None"] = relationship(  # noqa: F821
        "CaseCategory", foreign_keys=[CaseCategoryID]
    )
    gravity: Mapped["GravityOffence | None"] = relationship(  # noqa: F821
        "GravityOffence", foreign_keys=[GravityOffenceID]
    )
    crime_major_head: Mapped["CrimeHead | None"] = relationship(  # noqa: F821
        "CrimeHead", foreign_keys=[CrimeMajorHeadID]
    )
    crime_minor_head: Mapped["CrimeSubHead | None"] = relationship(  # noqa: F821
        "CrimeSubHead", foreign_keys=[CrimeMinorHeadID]
    )
    case_status: Mapped["CaseStatusMaster | None"] = relationship(  # noqa: F821
        "CaseStatusMaster", foreign_keys=[CaseStatusID]
    )

    # case-centric children
    complainants: Mapped[list["ComplainantDetails"]] = relationship(
        back_populates="case",
        cascade="save-update, merge",
    )
    victims: Mapped[list["Victim"]] = relationship(
        back_populates="case",
        cascade="save-update, merge",
    )
    accused: Mapped[list["Accused"]] = relationship(
        back_populates="case",
        cascade="save-update, merge",
    )
    arrests: Mapped[list["ArrestSurrender"]] = relationship(
        back_populates="case",
        cascade="save-update, merge",
    )
    act_sections: Mapped[list["ActSectionAssociation"]] = relationship(
        back_populates="case",
        cascade="save-update, merge",
    )
    chargesheet: Mapped["ChargesheetDetails | None"] = relationship(
        back_populates="case",
        cascade="save-update, merge",
        uselist=False,
    )
    evidence: Mapped[list["Evidence"]] = relationship(
        back_populates="case",
        cascade="save-update, merge",
    )
    recovered_items: Mapped[list["RecoveredItems"]] = relationship(
        back_populates="case",
        cascade="save-update, merge",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CaseMaster {self.CaseMasterID} {self.CrimeNo!r}>"


class ComplainantDetails(Base):
    """The person who reported the FIR."""

    __tablename__ = "ComplainantDetails"

    ComplainantID: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    CaseMasterID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("CaseMaster.CaseMasterID"), nullable=True
    )
    ComplainantName: Mapped[str] = mapped_column(String(200), nullable=False)
    AgeYear: Mapped[int | None] = mapped_column(Integer, nullable=True)
    OccupationID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("OccupationMaster.OccupationID"), nullable=True
    )
    ReligionID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("ReligionMaster.ReligionID"), nullable=True
    )
    CasteID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("CasteMaster.caste_master_id"), nullable=True
    )
    GenderID: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships ----------------------------------------------------------
    case: Mapped["CaseMaster | None"] = relationship(back_populates="complainants")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ComplainantDetails {self.ComplainantID} {self.ComplainantName!r}>"


class Victim(Base):
    """A victim of the case."""

    __tablename__ = "Victim"

    VictimMasterID: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    CaseMasterID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("CaseMaster.CaseMasterID"), nullable=True
    )
    VictimName: Mapped[str] = mapped_column(String(200), nullable=False)
    AgeYear: Mapped[int | None] = mapped_column(Integer, nullable=True)
    GenderID: Mapped[int | None] = mapped_column(Integer, nullable=True)
    VictimPolice: Mapped[str | None] = mapped_column(CHAR(1), default="0")
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_hash: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships ----------------------------------------------------------
    case: Mapped["CaseMaster | None"] = relationship(back_populates="victims")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Victim {self.VictimMasterID} {self.VictimName!r}>"


class Accused(Base):
    """A person accused of the crime."""

    __tablename__ = "Accused"

    AccusedMasterID: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    CaseMasterID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("CaseMaster.CaseMasterID"), nullable=True
    )
    AccusedName: Mapped[str] = mapped_column(String(200), nullable=False)
    AgeYear: Mapped[int | None] = mapped_column(Integer, nullable=True)
    GenderID: Mapped[int | None] = mapped_column(Integer, nullable=True)
    PersonID: Mapped[str | None] = mapped_column(String(10), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_known_criminal: Mapped[bool | None] = mapped_column(
        Boolean, default=False, nullable=True
    )
    criminal_history: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships ----------------------------------------------------------
    case: Mapped["CaseMaster | None"] = relationship(back_populates="accused")
    arrests: Mapped[list["ArrestSurrender"]] = relationship(
        back_populates="accused",
        cascade="save-update, merge",
    )
    recovered_items: Mapped[list["RecoveredItems"]] = relationship(
        back_populates="accused",
        cascade="save-update, merge",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Accused {self.AccusedMasterID} {self.AccusedName!r}>"


class ArrestSurrender(Base):
    """An arrest or surrender event tied to a case and an accused."""

    __tablename__ = "ArrestSurrender"

    ArrestSurrenderID: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    CaseMasterID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("CaseMaster.CaseMasterID"), nullable=True
    )
    ArrestSurrenderTypeID: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    ArrestSurrenderDate: Mapped[date | None] = mapped_column(Date, nullable=True)
    ArrestSurrenderStateId: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("State.StateID"), nullable=True
    )
    ArrestSurrenderDistrictId: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("District.DistrictID"), nullable=True
    )
    PoliceStationID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Unit.UnitID"), nullable=True
    )
    IOID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Employee.EmployeeID"), nullable=True
    )
    CourtID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Court.CourtID"), nullable=True
    )
    AccusedMasterID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Accused.AccusedMasterID"), nullable=True
    )
    IsAccused: Mapped[bool | None] = mapped_column(Boolean, default=True)
    IsComplainantAccused: Mapped[bool | None] = mapped_column(
        Boolean, default=False
    )

    # Relationships ----------------------------------------------------------
    case: Mapped["CaseMaster | None"] = relationship(back_populates="arrests")
    accused: Mapped["Accused | None"] = relationship(back_populates="arrests")

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<ArrestSurrender {self.ArrestSurrenderID} "
            f"accused={self.AccusedMasterID}>"
        )


class ActSectionAssociation(Base):
    """Which Act+Section(s) are charged on a case. M:N bridge with ordering."""

    __tablename__ = "ActSectionAssociation"

    CaseMasterID: Mapped[int] = mapped_column(
        Integer, ForeignKey("CaseMaster.CaseMasterID"), primary_key=True
    )
    ActID: Mapped[str] = mapped_column(
        String(50), ForeignKey("Act.ActCode"), primary_key=True
    )
    SectionID: Mapped[str] = mapped_column(String(50), primary_key=True)
    ActOrderID: Mapped[int | None] = mapped_column(Integer, nullable=True)
    SectionOrderID: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships ----------------------------------------------------------
    case: Mapped["CaseMaster | None"] = relationship(back_populates="act_sections")
    act: Mapped["Act | None"] = relationship("Act", foreign_keys=[ActID])

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<ActSectionAssociation case={self.CaseMasterID} "
            f"{self.ActID}/{self.SectionID}>"
        )


class ChargesheetDetails(Base):
    """One-to-one with CaseMaster: the chargesheet filed for the case."""

    __tablename__ = "ChargesheetDetails"

    CSID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    CaseMasterID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("CaseMaster.CaseMasterID"), nullable=True
    )
    csdate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cstype: Mapped[str | None] = mapped_column(CHAR(1), nullable=True)
    PolicePersonID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Employee.EmployeeID"), nullable=True
    )

    # Relationships ----------------------------------------------------------
    case: Mapped["CaseMaster | None"] = relationship(back_populates="chargesheet")
    filed_by: Mapped["Employee | None"] = relationship(  # noqa: F821
        "Employee", foreign_keys=[PolicePersonID]
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ChargesheetDetails {self.CSID} case={self.CaseMasterID}>"


class Evidence(Base):
    """Photo / file evidence attached to a case, with SHA-256 hash for chain-of-custody."""

    __tablename__ = "Evidence"

    EvidenceID: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    CaseMasterID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("CaseMaster.CaseMasterID"), nullable=True
    )
    evidence_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    gps_lat: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    gps_lng: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    collected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    uploaded_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Employee.EmployeeID"), nullable=True
    )
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships ----------------------------------------------------------
    case: Mapped["CaseMaster | None"] = relationship(back_populates="evidence")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Evidence {self.EvidenceID} {self.evidence_type!r}>"


class RecoveredItems(Base):
    """Items recovered from an accused as part of a case."""

    __tablename__ = "RecoveredItems"

    RecoveryID: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    CaseMasterID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("CaseMaster.CaseMasterID"), nullable=True
    )
    AccusedMasterID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Accused.AccusedMasterID"), nullable=True
    )
    item_description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    estimated_value: Mapped[float | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    recovery_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    recovery_location: Mapped[str | None] = mapped_column(Text, nullable=True)
    recovered_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Employee.EmployeeID"), nullable=True
    )
    witness_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    seizure_memo_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships ----------------------------------------------------------
    case: Mapped["CaseMaster | None"] = relationship(back_populates="recovered_items")
    accused: Mapped["Accused | None"] = relationship(back_populates="recovered_items")

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<RecoveredItems {self.RecoveryID} {self.item_description!r}>"
        )
