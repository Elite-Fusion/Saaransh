"""
SQLAlchemy ORM models — Crime Taxonomy group.

Lookup tables that classify crimes and the laws applied to them:
  - CaseCategory
  - GravityOffence
  - CaseStatusMaster
  - CrimeHead
  - CrimeSubHead
  - Act
  - Section
  - CrimeHeadActSection
  - OccupationMaster
  - ReligionMaster
  - CasteMaster
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.session import Base

if TYPE_CHECKING:
    pass  # these lookup tables are referenced from elsewhere via FKs only


class CaseCategory(Base):
    """FIR / UDR / PAR / Zero FIR."""

    __tablename__ = "CaseCategory"

    CaseCategoryID: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    LookupValue: Mapped[str] = mapped_column(String(50), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CaseCategory {self.CaseCategoryID} {self.LookupValue!r}>"


class GravityOffence(Base):
    """Heinous / Non-Heinous / Minor."""

    __tablename__ = "GravityOffence"

    GravityOffenceID: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    LookupValue: Mapped[str] = mapped_column(String(100), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<GravityOffence {self.GravityOffenceID} {self.LookupValue!r}>"


class CaseStatusMaster(Base):
    """Open / Under Investigation / Charge Sheeted / Closed / Undetected."""

    __tablename__ = "CaseStatusMaster"

    CaseStatusID: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    CaseStatusName: Mapped[str] = mapped_column(String(100), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CaseStatusMaster {self.CaseStatusID} {self.CaseStatusName!r}>"


class CrimeHead(Base):
    """Top-level crime group — e.g. 'Crimes Against Property'."""

    __tablename__ = "CrimeHead"

    CrimeHeadID: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    CrimeGroupName: Mapped[str] = mapped_column(String(200), nullable=False)
    Active: Mapped[bool | None] = mapped_column(Boolean, default=True)

    # Relationships ----------------------------------------------------------
    sub_heads: Mapped[list["CrimeSubHead"]] = relationship(
        back_populates="crime_head",
        cascade="save-update, merge",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CrimeHead {self.CrimeHeadID} {self.CrimeGroupName!r}>"


class CrimeSubHead(Base):
    """Specific crime type — e.g. 'Murder', 'Chain Snatching'."""

    __tablename__ = "CrimeSubHead"

    CrimeSubHeadID: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    CrimeHeadID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("CrimeHead.CrimeHeadID"), nullable=True
    )
    CrimeHeadName: Mapped[str] = mapped_column(String(200), nullable=False)
    SeqID: Mapped[int | None] = mapped_column(Integer, nullable=True)
    Active: Mapped[bool | None] = mapped_column(Boolean, default=True)

    # Relationships ----------------------------------------------------------
    crime_head: Mapped["CrimeHead | None"] = relationship(back_populates="sub_heads")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CrimeSubHead {self.CrimeSubHeadID} {self.CrimeHeadName!r}>"


class Act(Base):
    """A law — IPC, BNS, NDPS, IT, DV Act."""

    __tablename__ = "Act"

    ActCode: Mapped[str] = mapped_column(String(50), primary_key=True)
    ActDescription: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ShortName: Mapped[str | None] = mapped_column(String(100), nullable=True)
    Active: Mapped[bool | None] = mapped_column(Boolean, default=True)

    # Relationships ----------------------------------------------------------
    sections: Mapped[list["Section"]] = relationship(back_populates="act")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Act {self.ActCode!r}>"


class Section(Base):
    """A section of an Act — composite PK (SectionCode, ActCode)."""

    __tablename__ = "Section"

    SectionCode: Mapped[str] = mapped_column(String(50), primary_key=True)
    ActCode: Mapped[str] = mapped_column(
        String(50), ForeignKey("Act.ActCode"), primary_key=True
    )
    SectionDescription: Mapped[str | None] = mapped_column(String(500), nullable=True)
    Active: Mapped[bool | None] = mapped_column(Boolean, default=True)

    # Relationships ----------------------------------------------------------
    act: Mapped["Act | None"] = relationship(back_populates="sections")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Section {self.SectionCode!r}/{self.ActCode!r}>"


class CrimeHeadActSection(Base):
    """M:N bridge: which sections apply to which crime head."""

    __tablename__ = "CrimeHeadActSection"

    CrimeHeadID: Mapped[int] = mapped_column(
        Integer, ForeignKey("CrimeHead.CrimeHeadID"), primary_key=True
    )
    ActCode: Mapped[str] = mapped_column(
        String(50), ForeignKey("Act.ActCode"), primary_key=True
    )
    SectionCode: Mapped[str] = mapped_column(String(50), primary_key=True)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<CrimeHeadActSection head={self.CrimeHeadID} "
            f"{self.ActCode}/{self.SectionCode}>"
        )


class OccupationMaster(Base):
    """Occupation lookup — Farmer, Student, etc."""

    __tablename__ = "OccupationMaster"

    OccupationID: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    OccupationName: Mapped[str] = mapped_column(String(100), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<OccupationMaster {self.OccupationID} {self.OccupationName!r}>"


class ReligionMaster(Base):
    """Religion lookup — Hindu, Muslim, …"""

    __tablename__ = "ReligionMaster"

    ReligionID: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    ReligionName: Mapped[str] = mapped_column(String(100), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ReligionMaster {self.ReligionID} {self.ReligionName!r}>"


class CasteMaster(Base):
    """Caste category lookup — SC, ST, OBC, General."""

    __tablename__ = "CasteMaster"

    caste_master_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    caste_master_name: Mapped[str] = mapped_column(String(100), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CasteMaster {self.caste_master_id} {self.caste_master_name!r}>"
