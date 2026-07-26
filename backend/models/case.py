"""
SQLAlchemy ORM models — Case Core group.

Column names match the Supabase schema exactly (all lowercase).
Python attribute names are unchanged for backward compatibility.
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
    __tablename__ = "casemaster"

    CaseMasterID: Mapped[int] = mapped_column("casemasterid", Integer, primary_key=True, autoincrement=True)
    CrimeNo: Mapped[str] = mapped_column("crimeno", String(50), unique=True, nullable=False)
    CaseNo: Mapped[str | None] = mapped_column("caseno", String(20), nullable=True)
    CrimeRegisteredDate: Mapped[date] = mapped_column("crimeregistereddate", Date, nullable=False)
    PolicePersonID: Mapped[int | None] = mapped_column("policepersonid", Integer, ForeignKey("employee.employeeid"), nullable=True)
    PoliceStationID: Mapped[int | None] = mapped_column("policestationid", Integer, ForeignKey("unit.unitid"), nullable=True)
    CaseCategoryID: Mapped[int | None] = mapped_column("casecategoryid", Integer, ForeignKey("casecategory.casecategoryid"), nullable=True)
    GravityOffenceID: Mapped[int | None] = mapped_column("gravityoffenceid", Integer, ForeignKey("gravityoffence.gravityoffenceid"), nullable=True)
    CrimeMajorHeadID: Mapped[int | None] = mapped_column("crimemajorheadid", Integer, ForeignKey("crimehead.crimeheadid"), nullable=True)
    CrimeMinorHeadID: Mapped[int | None] = mapped_column("crimeminorheadid", Integer, ForeignKey("crimesubhead.crimesubheadid"), nullable=True)
    CaseStatusID: Mapped[int | None] = mapped_column("casestatusid", Integer, ForeignKey("casestatusmaster.casestatusid"), nullable=True)
    CourtID: Mapped[int | None] = mapped_column("courtid", Integer, ForeignKey("court.courtid"), nullable=True)
    IncidentFromDate: Mapped[datetime | None] = mapped_column("incidentfromdate", DateTime, nullable=True)
    IncidentToDate: Mapped[datetime | None] = mapped_column("incidenttodate", DateTime, nullable=True)
    InfoReceivedPSDate: Mapped[datetime | None] = mapped_column("inforeceivedpsdate", DateTime, nullable=True)
    latitude: Mapped[float | None] = mapped_column("latitude", Numeric(9, 6), nullable=True)
    longitude: Mapped[float | None] = mapped_column("longitude", Numeric(9, 6), nullable=True)
    BriefFacts: Mapped[str | None] = mapped_column("brieffacts", Text, nullable=True)
    mo_embedding: Mapped[list[float] | None] = mapped_column("mo_embedding", Vector(384), nullable=True)
    is_series_crime: Mapped[bool | None] = mapped_column("is_series_crime", Boolean, default=False, nullable=True)
    series_id: Mapped[int | None] = mapped_column("series_id", Integer, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column("created_at", DateTime, default=None, nullable=True)

    # Relationships
    police_station: Mapped["Unit | None"] = relationship("Unit", foreign_keys=[PoliceStationID])
    investigating_officer: Mapped["Employee | None"] = relationship("Employee", foreign_keys=[PolicePersonID])
    court: Mapped["Court | None"] = relationship("Court", foreign_keys=[CourtID])
    case_category: Mapped["CaseCategory | None"] = relationship("CaseCategory", foreign_keys=[CaseCategoryID])
    gravity: Mapped["GravityOffence | None"] = relationship("GravityOffence", foreign_keys=[GravityOffenceID])
    crime_major_head: Mapped["CrimeHead | None"] = relationship("CrimeHead", foreign_keys=[CrimeMajorHeadID])
    crime_minor_head: Mapped["CrimeSubHead | None"] = relationship("CrimeSubHead", foreign_keys=[CrimeMinorHeadID])
    case_status: Mapped["CaseStatusMaster | None"] = relationship("CaseStatusMaster", foreign_keys=[CaseStatusID])

    complainants: Mapped[list["ComplainantDetails"]] = relationship(back_populates="case", cascade="save-update, merge")
    victims: Mapped[list["Victim"]] = relationship(back_populates="case", cascade="save-update, merge")
    accused: Mapped[list["Accused"]] = relationship(back_populates="case", cascade="save-update, merge")
    arrests: Mapped[list["ArrestSurrender"]] = relationship(back_populates="case", cascade="save-update, merge")
    act_sections: Mapped[list["ActSectionAssociation"]] = relationship(back_populates="case", cascade="save-update, merge")
    chargesheet: Mapped["ChargesheetDetails | None"] = relationship(back_populates="case", cascade="save-update, merge", uselist=False)
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="case", cascade="save-update, merge")
    recovered_items: Mapped[list["RecoveredItems"]] = relationship(back_populates="case", cascade="save-update, merge")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CaseMaster {self.CaseMasterID} {self.CrimeNo!r}>"


class ComplainantDetails(Base):
    __tablename__ = "complainantdetails"

    ComplainantID: Mapped[int] = mapped_column("complainantid", Integer, primary_key=True, autoincrement=True)
    CaseMasterID: Mapped[int | None] = mapped_column("casemasterid", Integer, ForeignKey("casemaster.casemasterid"), nullable=True)
    ComplainantName: Mapped[str] = mapped_column("complainantname", String(200), nullable=False)
    AgeYear: Mapped[int | None] = mapped_column("ageyear", Integer, nullable=True)
    OccupationID: Mapped[int | None] = mapped_column("occupationid", Integer, ForeignKey("occupationmaster.occupationid"), nullable=True)
    ReligionID: Mapped[int | None] = mapped_column("religionid", Integer, ForeignKey("religionmaster.religionid"), nullable=True)
    CasteID: Mapped[int | None] = mapped_column("casteid", Integer, ForeignKey("castemaster.caste_master_id"), nullable=True)
    GenderID: Mapped[int | None] = mapped_column("genderid", Integer, nullable=True)

    case: Mapped["CaseMaster | None"] = relationship(back_populates="complainants")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ComplainantDetails {self.ComplainantID} {self.ComplainantName!r}>"


class Victim(Base):
    __tablename__ = "victim"

    VictimMasterID: Mapped[int] = mapped_column("victimmasterid", Integer, primary_key=True, autoincrement=True)
    CaseMasterID: Mapped[int | None] = mapped_column("casemasterid", Integer, ForeignKey("casemaster.casemasterid"), nullable=True)
    VictimName: Mapped[str] = mapped_column("victimname", String(200), nullable=False)
    AgeYear: Mapped[int | None] = mapped_column("ageyear", Integer, nullable=True)
    GenderID: Mapped[int | None] = mapped_column("genderid", Integer, nullable=True)
    VictimPolice: Mapped[str | None] = mapped_column("victimpolice", String(1), default="0")
    photo_url: Mapped[str | None] = mapped_column("photo_url", Text, nullable=True)
    photo_hash: Mapped[str | None] = mapped_column("photo_hash", Text, nullable=True)

    case: Mapped["CaseMaster | None"] = relationship(back_populates="victims")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Victim {self.VictimMasterID} {self.VictimName!r}>"


class Accused(Base):
    __tablename__ = "accused"

    AccusedMasterID: Mapped[int] = mapped_column("accusedmasterid", Integer, primary_key=True, autoincrement=True)
    CaseMasterID: Mapped[int | None] = mapped_column("casemasterid", Integer, ForeignKey("casemaster.casemasterid"), nullable=True)
    AccusedName: Mapped[str] = mapped_column("accusedname", String(200), nullable=False)
    AgeYear: Mapped[int | None] = mapped_column("ageyear", Integer, nullable=True)
    GenderID: Mapped[int | None] = mapped_column("genderid", Integer, nullable=True)
    PersonID: Mapped[str | None] = mapped_column("personid", String(10), nullable=True)
    photo_url: Mapped[str | None] = mapped_column("photo_url", Text, nullable=True)
    photo_hash: Mapped[str | None] = mapped_column("photo_hash", Text, nullable=True)
    address: Mapped[str | None] = mapped_column("address", Text, nullable=True)
    is_known_criminal: Mapped[bool | None] = mapped_column("is_known_criminal", Boolean, default=False, nullable=True)
    criminal_history: Mapped[str | None] = mapped_column("criminal_history", Text, nullable=True)

    case: Mapped["CaseMaster | None"] = relationship(back_populates="accused")
    arrests: Mapped[list["ArrestSurrender"]] = relationship(back_populates="accused", cascade="save-update, merge")
    recovered_items: Mapped[list["RecoveredItems"]] = relationship(back_populates="accused", cascade="save-update, merge")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Accused {self.AccusedMasterID} {self.AccusedName!r}>"


class ArrestSurrender(Base):
    __tablename__ = "arrestsurrender"

    ArrestSurrenderID: Mapped[int] = mapped_column("arrestsurrenderid", Integer, primary_key=True, autoincrement=True)
    CaseMasterID: Mapped[int | None] = mapped_column("casemasterid", Integer, ForeignKey("casemaster.casemasterid"), nullable=True)
    ArrestSurrenderTypeID: Mapped[int | None] = mapped_column("arrestsurrendertypeid", Integer, nullable=True)
    ArrestSurrenderDate: Mapped[date | None] = mapped_column("arrestsurrenderdate", Date, nullable=True)
    ArrestSurrenderStateId: Mapped[int | None] = mapped_column("arrestsurrenderstateid", Integer, ForeignKey("state.stateid"), nullable=True)
    ArrestSurrenderDistrictId: Mapped[int | None] = mapped_column("arrestsurrenderdistrictid", Integer, ForeignKey("district.districtid"), nullable=True)
    PoliceStationID: Mapped[int | None] = mapped_column("policestationid", Integer, ForeignKey("unit.unitid"), nullable=True)
    IOID: Mapped[int | None] = mapped_column("ioid", Integer, ForeignKey("employee.employeeid"), nullable=True)
    CourtID: Mapped[int | None] = mapped_column("courtid", Integer, ForeignKey("court.courtid"), nullable=True)
    AccusedMasterID: Mapped[int | None] = mapped_column("accusedmasterid", Integer, ForeignKey("accused.accusedmasterid"), nullable=True)
    IsAccused: Mapped[bool | None] = mapped_column("isaccused", Boolean, default=True)
    IsComplainantAccused: Mapped[bool | None] = mapped_column("iscomplainantaccused", Boolean, default=False)

    case: Mapped["CaseMaster | None"] = relationship(back_populates="arrests")
    accused: Mapped["Accused | None"] = relationship(back_populates="arrests")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ArrestSurrender {self.ArrestSurrenderID} accused={self.AccusedMasterID}>"


class ActSectionAssociation(Base):
    __tablename__ = "actsectionassociation"

    CaseMasterID: Mapped[int] = mapped_column("casemasterid", Integer, ForeignKey("casemaster.casemasterid"), primary_key=True)
    ActID: Mapped[str] = mapped_column("actid", String(50), ForeignKey("act.actcode"), primary_key=True)
    SectionID: Mapped[str] = mapped_column("sectionid", String(50), primary_key=True)
    ActOrderID: Mapped[int | None] = mapped_column("actorderid", Integer, nullable=True)
    SectionOrderID: Mapped[int | None] = mapped_column("sectionorderid", Integer, nullable=True)

    case: Mapped["CaseMaster | None"] = relationship(back_populates="act_sections")
    act: Mapped["Act | None"] = relationship("Act", foreign_keys=[ActID])

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ActSectionAssociation case={self.CaseMasterID} {self.ActID}/{self.SectionID}>"


class ChargesheetDetails(Base):
    __tablename__ = "chargesheetdetails"

    CSID: Mapped[int] = mapped_column("csid", Integer, primary_key=True, autoincrement=True)
    CaseMasterID: Mapped[int | None] = mapped_column("casemasterid", Integer, ForeignKey("casemaster.casemasterid"), nullable=True)
    csdate: Mapped[datetime | None] = mapped_column("csdate", DateTime, nullable=True)
    cstype: Mapped[str | None] = mapped_column("cstype", CHAR(1), nullable=True)
    PolicePersonID: Mapped[int | None] = mapped_column("policepersonid", Integer, ForeignKey("employee.employeeid"), nullable=True)

    case: Mapped["CaseMaster | None"] = relationship(back_populates="chargesheet")
    filed_by: Mapped["Employee | None"] = relationship("Employee", foreign_keys=[PolicePersonID])

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ChargesheetDetails {self.CSID} case={self.CaseMasterID}>"


class Evidence(Base):
    __tablename__ = "evidence"

    EvidenceID: Mapped[int] = mapped_column("evidenceid", Integer, primary_key=True, autoincrement=True)
    CaseMasterID: Mapped[int | None] = mapped_column("casemasterid", Integer, ForeignKey("casemaster.casemasterid"), nullable=True)
    evidence_type: Mapped[str | None] = mapped_column("evidence_type", String(50), nullable=True)
    file_url: Mapped[str | None] = mapped_column("file_url", Text, nullable=True)
    file_hash: Mapped[str | None] = mapped_column("file_hash", Text, nullable=True)
    description: Mapped[str | None] = mapped_column("description", Text, nullable=True)
    gps_lat: Mapped[float | None] = mapped_column("gps_lat", Numeric(9, 6), nullable=True)
    gps_lng: Mapped[float | None] = mapped_column("gps_lng", Numeric(9, 6), nullable=True)
    collected_at: Mapped[datetime | None] = mapped_column("collected_at", DateTime, nullable=True)
    uploaded_by: Mapped[int | None] = mapped_column("uploaded_by", Integer, ForeignKey("employee.employeeid"), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column("created_at", DateTime, nullable=True)

    case: Mapped["CaseMaster | None"] = relationship(back_populates="evidence")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Evidence {self.EvidenceID} {self.evidence_type!r}>"


class RecoveredItems(Base):
    __tablename__ = "recovereditems"

    RecoveryID: Mapped[int] = mapped_column("recoveryid", Integer, primary_key=True, autoincrement=True)
    CaseMasterID: Mapped[int | None] = mapped_column("casemasterid", Integer, ForeignKey("casemaster.casemasterid"), nullable=True)
    AccusedMasterID: Mapped[int | None] = mapped_column("accusedmasterid", Integer, ForeignKey("accused.accusedmasterid"), nullable=True)
    item_description: Mapped[str] = mapped_column("item_description", Text, nullable=False)
    quantity: Mapped[str | None] = mapped_column("quantity", String(50), nullable=True)
    estimated_value: Mapped[float | None] = mapped_column("estimated_value", Numeric(12, 2), nullable=True)
    photo_url: Mapped[str | None] = mapped_column("photo_url", Text, nullable=True)
    photo_hash: Mapped[str | None] = mapped_column("photo_hash", Text, nullable=True)
    recovery_date: Mapped[datetime | None] = mapped_column("recovery_date", DateTime, nullable=True)
    recovery_location: Mapped[str | None] = mapped_column("recovery_location", Text, nullable=True)
    recovered_by: Mapped[int | None] = mapped_column("recovered_by", Integer, ForeignKey("employee.employeeid"), nullable=True)
    witness_name: Mapped[str | None] = mapped_column("witness_name", Text, nullable=True)
    seizure_memo_ref: Mapped[str | None] = mapped_column("seizure_memo_ref", Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column("created_at", DateTime, nullable=True)

    case: Mapped["CaseMaster | None"] = relationship(back_populates="recovered_items")
    accused: Mapped["Accused | None"] = relationship(back_populates="recovered_items")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RecoveredItems {self.RecoveryID} {self.item_description!r}>"
