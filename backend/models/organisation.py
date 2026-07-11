"""
SQLAlchemy ORM models — Organisation Structure group.

Tables describing the police hierarchy and the people in it:
  - UnitType
  - Unit
  - Rank
  - Designation
  - Employee
  - Court
"""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.session import Base

if TYPE_CHECKING:
    from backend.models.geography import District, State


class UnitType(Base):
    """Type of police unit — Police Station, Circle Office, SP Office, etc."""

    __tablename__ = "UnitType"

    UnitTypeID: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    UnitTypeName: Mapped[str] = mapped_column(String(100), nullable=False)
    CityDistState: Mapped[str | None] = mapped_column(String(20), nullable=True)
    Hierarchy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    Active: Mapped[bool | None] = mapped_column(Boolean, default=True)

    # Relationships ----------------------------------------------------------
    units: Mapped[list["Unit"]] = relationship(back_populates="unit_type")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<UnitType {self.UnitTypeID} {self.UnitTypeName!r}>"


class Unit(Base):
    """A physical police unit (a station, circle, or SP office)."""

    __tablename__ = "Unit"

    UnitID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    UnitName: Mapped[str] = mapped_column(String(200), nullable=False)
    TypeID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("UnitType.UnitTypeID"), nullable=True
    )
    ParentUnit: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Unit.UnitID"), nullable=True
    )
    StateID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("State.StateID"), nullable=True
    )
    DistrictID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("District.DistrictID"), nullable=True
    )
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    Active: Mapped[bool | None] = mapped_column(Boolean, default=True)

    # Relationships ----------------------------------------------------------
    unit_type: Mapped["UnitType | None"] = relationship(back_populates="units")
    state: Mapped["State | None"] = relationship(
        back_populates="units", foreign_keys=[StateID]
    )
    district: Mapped["District | None"] = relationship(
        back_populates="units", foreign_keys=[DistrictID]
    )

    # self-referential hierarchy (a circle contains stations)
    parent: Mapped["Unit | None"] = relationship(
        remote_side="Unit.UnitID", back_populates="children"
    )
    children: Mapped[list["Unit"]] = relationship(back_populates="parent")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Unit {self.UnitID} {self.UnitName!r}>"


class Rank(Base):
    """Police rank — DGP down to Constable. Used for ordering the hierarchy."""

    __tablename__ = "Rank"

    RankID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    RankName: Mapped[str] = mapped_column(String(100), nullable=False)
    Hierarchy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    Active: Mapped[bool | None] = mapped_column(Boolean, default=True)

    # Relationships ----------------------------------------------------------
    employees: Mapped[list["Employee"]] = relationship(back_populates="rank")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Rank {self.RankID} {self.RankName!r}>"


class Designation(Base):
    """Job role within the police — IO, SHO, CI, etc."""

    __tablename__ = "Designation"

    DesignationID: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    DesignationName: Mapped[str] = mapped_column(String(100), nullable=False)
    SortOrder: Mapped[int | None] = mapped_column(Integer, nullable=True)
    Active: Mapped[bool | None] = mapped_column(Boolean, default=True)

    # Relationships ----------------------------------------------------------
    employees: Mapped[list["Employee"]] = relationship(back_populates="designation")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Designation {self.DesignationID} {self.DesignationName!r}>"


class Employee(Base):
    """A police officer. The seed file maps 8 officers (Rajesh Kumar, Priya Nair, …)."""

    __tablename__ = "Employee"

    EmployeeID: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    DistrictID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("District.DistrictID"), nullable=True
    )
    UnitID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Unit.UnitID"), nullable=True
    )
    RankID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Rank.RankID"), nullable=True
    )
    DesignationID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Designation.DesignationID"), nullable=True
    )
    KGID: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    FirstName: Mapped[str] = mapped_column(String(100), nullable=False)
    EmployeeDOB: Mapped[date | None] = mapped_column(Date, nullable=True)
    GenderID: Mapped[int | None] = mapped_column(Integer, nullable=True)
    BloodGroupID: Mapped[int | None] = mapped_column(Integer, nullable=True)
    PhysicallyChallenged: Mapped[bool | None] = mapped_column(
        Boolean, default=False, nullable=True
    )
    AppointmentDate: Mapped[date | None] = mapped_column(Date, nullable=True)
    Active: Mapped[bool | None] = mapped_column(Boolean, default=True)

    # Relationships ----------------------------------------------------------
    district: Mapped["District | None"] = relationship(  # noqa: F821
        "District", foreign_keys=[DistrictID]
    )
    unit: Mapped["Unit | None"] = relationship(  # noqa: F821
        "Unit", foreign_keys=[UnitID]
    )
    rank: Mapped["Rank | None"] = relationship(back_populates="employees")
    designation: Mapped["Designation | None"] = relationship(back_populates="employees")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Employee {self.EmployeeID} {self.FirstName!r}>"


class Court(Base):
    """A court where cases may be heard."""

    __tablename__ = "Court"

    CourtID: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    CourtName: Mapped[str] = mapped_column(String(200), nullable=False)
    DistrictID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("District.DistrictID"), nullable=True
    )
    StateID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("State.StateID"), nullable=True
    )
    Active: Mapped[bool | None] = mapped_column(Boolean, default=True)

    # Relationships ----------------------------------------------------------
    district: Mapped["District | None"] = relationship()  # noqa: F821
    state: Mapped["State | None"] = relationship(back_populates="courts")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Court {self.CourtID} {self.CourtName!r}>"
