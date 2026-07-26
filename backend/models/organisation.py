"""
SQLAlchemy ORM models — Organisation Structure group.

Column names match the Supabase schema exactly (all lowercase).
Python attribute names are unchanged for backward compatibility.
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
    __tablename__ = "unittype"

    UnitTypeID: Mapped[int] = mapped_column("unittypeid", Integer, primary_key=True, autoincrement=True)
    UnitTypeName: Mapped[str] = mapped_column("unittypename", String(100), nullable=False)
    CityDistState: Mapped[str | None] = mapped_column("citydiststate", String(20), nullable=True)
    Hierarchy: Mapped[int | None] = mapped_column("hierarchy", Integer, nullable=True)
    Active: Mapped[bool | None] = mapped_column("active", Boolean, default=True)

    units: Mapped[list["Unit"]] = relationship(back_populates="unit_type")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<UnitType {self.UnitTypeID} {self.UnitTypeName!r}>"


class Unit(Base):
    __tablename__ = "unit"

    UnitID: Mapped[int] = mapped_column("unitid", Integer, primary_key=True, autoincrement=True)
    UnitName: Mapped[str] = mapped_column("unitname", String(200), nullable=False)
    TypeID: Mapped[int | None] = mapped_column("typeid", Integer, ForeignKey("unittype.unittypeid"), nullable=True)
    ParentUnit: Mapped[int | None] = mapped_column("parentunit", Integer, ForeignKey("unit.unitid"), nullable=True)
    StateID: Mapped[int | None] = mapped_column("stateid", Integer, ForeignKey("state.stateid"), nullable=True)
    DistrictID: Mapped[int | None] = mapped_column("districtid", Integer, ForeignKey("district.districtid"), nullable=True)
    latitude: Mapped[float | None] = mapped_column("latitude", Numeric(9, 6), nullable=True)
    longitude: Mapped[float | None] = mapped_column("longitude", Numeric(9, 6), nullable=True)
    Active: Mapped[bool | None] = mapped_column("active", Boolean, default=True)

    unit_type: Mapped["UnitType | None"] = relationship(back_populates="units")
    state: Mapped["State | None"] = relationship(back_populates="units", foreign_keys=[StateID])
    district: Mapped["District | None"] = relationship(back_populates="units", foreign_keys=[DistrictID])
    parent: Mapped["Unit | None"] = relationship(remote_side="Unit.UnitID", back_populates="children")
    children: Mapped[list["Unit"]] = relationship(back_populates="parent")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Unit {self.UnitID} {self.UnitName!r}>"


class Rank(Base):
    __tablename__ = "rank"

    RankID: Mapped[int] = mapped_column("rankid", Integer, primary_key=True, autoincrement=True)
    RankName: Mapped[str] = mapped_column("rankname", String(100), nullable=False)
    Hierarchy: Mapped[int | None] = mapped_column("hierarchy", Integer, nullable=True)
    Active: Mapped[bool | None] = mapped_column("active", Boolean, default=True)

    employees: Mapped[list["Employee"]] = relationship(back_populates="rank")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Rank {self.RankID} {self.RankName!r}>"


class Designation(Base):
    __tablename__ = "designation"

    DesignationID: Mapped[int] = mapped_column("designationid", Integer, primary_key=True, autoincrement=True)
    DesignationName: Mapped[str] = mapped_column("designationname", String(100), nullable=False)
    SortOrder: Mapped[int | None] = mapped_column("sortorder", Integer, nullable=True)
    Active: Mapped[bool | None] = mapped_column("active", Boolean, default=True)

    employees: Mapped[list["Employee"]] = relationship(back_populates="designation")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Designation {self.DesignationID} {self.DesignationName!r}>"


class Employee(Base):
    __tablename__ = "employee"

    EmployeeID: Mapped[int] = mapped_column("employeeid", Integer, primary_key=True, autoincrement=True)
    DistrictID: Mapped[int | None] = mapped_column("districtid", Integer, ForeignKey("district.districtid"), nullable=True)
    UnitID: Mapped[int | None] = mapped_column("unitid", Integer, ForeignKey("unit.unitid"), nullable=True)
    RankID: Mapped[int | None] = mapped_column("rankid", Integer, ForeignKey("rank.rankid"), nullable=True)
    DesignationID: Mapped[int | None] = mapped_column("designationid", Integer, ForeignKey("designation.designationid"), nullable=True)
    KGID: Mapped[str | None] = mapped_column("kgid", String(50), unique=True, nullable=True)
    FirstName: Mapped[str] = mapped_column("firstname", String(100), nullable=False)
    EmployeeDOB: Mapped[date | None] = mapped_column("employeedob", Date, nullable=True)
    GenderID: Mapped[int | None] = mapped_column("genderid", Integer, nullable=True)
    BloodGroupID: Mapped[int | None] = mapped_column("bloodgroupid", Integer, nullable=True)
    PhysicallyChallenged: Mapped[bool | None] = mapped_column("physicallychallenged", Boolean, default=False, nullable=True)
    AppointmentDate: Mapped[date | None] = mapped_column("appointmentdate", Date, nullable=True)
    Active: Mapped[bool | None] = mapped_column("active", Boolean, default=True)

    district: Mapped["District | None"] = relationship("District", foreign_keys=[DistrictID])
    unit: Mapped["Unit | None"] = relationship("Unit", foreign_keys=[UnitID])
    rank: Mapped["Rank | None"] = relationship(back_populates="employees")
    designation: Mapped["Designation | None"] = relationship(back_populates="employees")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Employee {self.EmployeeID} {self.FirstName!r}>"


class Court(Base):
    __tablename__ = "court"

    CourtID: Mapped[int] = mapped_column("courtid", Integer, primary_key=True, autoincrement=True)
    CourtName: Mapped[str] = mapped_column("courtname", String(200), nullable=False)
    DistrictID: Mapped[int | None] = mapped_column("districtid", Integer, ForeignKey("district.districtid"), nullable=True)
    StateID: Mapped[int | None] = mapped_column("stateid", Integer, ForeignKey("state.stateid"), nullable=True)
    Active: Mapped[bool | None] = mapped_column("active", Boolean, default=True)

    district: Mapped["District | None"] = relationship()
    state: Mapped["State | None"] = relationship(back_populates="courts")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Court {self.CourtID} {self.CourtName!r}>"
