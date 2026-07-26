"""
SQLAlchemy ORM models — Crime Taxonomy group.

Column names match the Supabase schema exactly (all lowercase).
Python attribute names are unchanged for backward compatibility.
"""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.session import Base


class CaseCategory(Base):
    __tablename__ = "casecategory"

    CaseCategoryID: Mapped[int] = mapped_column("casecategoryid", Integer, primary_key=True, autoincrement=True)
    LookupValue: Mapped[str] = mapped_column("lookupvalue", String(50), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CaseCategory {self.CaseCategoryID} {self.LookupValue!r}>"


class GravityOffence(Base):
    __tablename__ = "gravityoffence"

    GravityOffenceID: Mapped[int] = mapped_column("gravityoffenceid", Integer, primary_key=True, autoincrement=True)
    LookupValue: Mapped[str] = mapped_column("lookupvalue", String(100), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<GravityOffence {self.GravityOffenceID} {self.LookupValue!r}>"


class CaseStatusMaster(Base):
    __tablename__ = "casestatusmaster"

    CaseStatusID: Mapped[int] = mapped_column("casestatusid", Integer, primary_key=True, autoincrement=True)
    CaseStatusName: Mapped[str] = mapped_column("casestatusname", String(100), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CaseStatusMaster {self.CaseStatusID} {self.CaseStatusName!r}>"


class CrimeHead(Base):
    __tablename__ = "crimehead"

    CrimeHeadID: Mapped[int] = mapped_column("crimeheadid", Integer, primary_key=True, autoincrement=True)
    CrimeGroupName: Mapped[str] = mapped_column("crimegroupname", String(200), nullable=False)
    Active: Mapped[bool | None] = mapped_column("active", Boolean, default=True)

    sub_heads: Mapped[list["CrimeSubHead"]] = relationship(back_populates="crime_head", cascade="save-update, merge")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CrimeHead {self.CrimeHeadID} {self.CrimeGroupName!r}>"


class CrimeSubHead(Base):
    __tablename__ = "crimesubhead"

    CrimeSubHeadID: Mapped[int] = mapped_column("crimesubheadid", Integer, primary_key=True, autoincrement=True)
    CrimeHeadID: Mapped[int | None] = mapped_column("crimeheadid", Integer, ForeignKey("crimehead.crimeheadid"), nullable=True)
    CrimeHeadName: Mapped[str] = mapped_column("crimeheadname", String(200), nullable=False)
    SeqID: Mapped[int | None] = mapped_column("seqid", Integer, nullable=True)
    Active: Mapped[bool | None] = mapped_column("active", Boolean, default=True)

    crime_head: Mapped["CrimeHead | None"] = relationship(back_populates="sub_heads")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CrimeSubHead {self.CrimeSubHeadID} {self.CrimeHeadName!r}>"


class Act(Base):
    __tablename__ = "act"

    ActCode: Mapped[str] = mapped_column("actcode", String(50), primary_key=True)
    ActDescription: Mapped[str | None] = mapped_column("actdescription", String(500), nullable=True)
    ShortName: Mapped[str | None] = mapped_column("shortname", String(100), nullable=True)
    Active: Mapped[bool | None] = mapped_column("active", Boolean, default=True)

    sections: Mapped[list["Section"]] = relationship(back_populates="act")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Act {self.ActCode!r}>"


class Section(Base):
    __tablename__ = "section"

    SectionCode: Mapped[str] = mapped_column("sectioncode", String(50), primary_key=True)
    ActCode: Mapped[str] = mapped_column("actcode", String(50), ForeignKey("act.actcode"), primary_key=True)
    SectionDescription: Mapped[str | None] = mapped_column("sectiondescription", String(500), nullable=True)
    Active: Mapped[bool | None] = mapped_column("active", Boolean, default=True)

    act: Mapped["Act | None"] = relationship(back_populates="sections")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Section {self.SectionCode!r}/{self.ActCode!r}>"


class CrimeHeadActSection(Base):
    __tablename__ = "crimeheadactsection"

    CrimeHeadID: Mapped[int] = mapped_column("crimeheadid", Integer, ForeignKey("crimehead.crimeheadid"), primary_key=True)
    ActCode: Mapped[str] = mapped_column("actcode", String(50), ForeignKey("act.actcode"), primary_key=True)
    SectionCode: Mapped[str] = mapped_column("sectioncode", String(50), primary_key=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CrimeHeadActSection head={self.CrimeHeadID} {self.ActCode}/{self.SectionCode}>"


class OccupationMaster(Base):
    __tablename__ = "occupationmaster"

    OccupationID: Mapped[int] = mapped_column("occupationid", Integer, primary_key=True, autoincrement=True)
    OccupationName: Mapped[str] = mapped_column("occupationname", String(100), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<OccupationMaster {self.OccupationID} {self.OccupationName!r}>"


class ReligionMaster(Base):
    __tablename__ = "religionmaster"

    ReligionID: Mapped[int] = mapped_column("religionid", Integer, primary_key=True, autoincrement=True)
    ReligionName: Mapped[str] = mapped_column("religionname", String(100), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ReligionMaster {self.ReligionID} {self.ReligionName!r}>"


class CasteMaster(Base):
    __tablename__ = "castemaster"

    caste_master_id: Mapped[int] = mapped_column("caste_master_id", Integer, primary_key=True, autoincrement=True)
    caste_master_name: Mapped[str] = mapped_column("caste_master_name", String(100), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CasteMaster {self.caste_master_id} {self.caste_master_name!r}>"
