"""
SQLAlchemy ORM models — Geography group.

Column names match the Supabase schema exactly (all lowercase).
Python attribute names are unchanged for backward compatibility.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.session import Base

if TYPE_CHECKING:
    from backend.models.organisation import Court, Unit


class State(Base):
    __tablename__ = "state"

    StateID: Mapped[int] = mapped_column("stateid", Integer, primary_key=True, autoincrement=True)
    StateName: Mapped[str] = mapped_column("statename", String(100), nullable=False)
    NationalityID: Mapped[int | None] = mapped_column("nationalityid", Integer, nullable=True)
    Active: Mapped[bool | None] = mapped_column("active", Boolean, default=True)

    districts: Mapped[list["District"]] = relationship(back_populates="state", cascade="save-update, merge")
    units: Mapped[list["Unit"]] = relationship(back_populates="state", cascade="save-update, merge", foreign_keys="Unit.StateID")
    courts: Mapped[list["Court"]] = relationship(back_populates="state", cascade="save-update, merge")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<State {self.StateID} {self.StateName!r}>"


class District(Base):
    __tablename__ = "district"

    DistrictID: Mapped[int] = mapped_column("districtid", Integer, primary_key=True, autoincrement=True)
    DistrictName: Mapped[str] = mapped_column("districtname", String(100), nullable=False)
    StateID: Mapped[int | None] = mapped_column("stateid", Integer, ForeignKey("state.stateid"), nullable=True)
    Active: Mapped[bool | None] = mapped_column("active", Boolean, default=True)

    state: Mapped["State | None"] = relationship(back_populates="districts")
    units: Mapped[list["Unit"]] = relationship(back_populates="district", cascade="save-update, merge", foreign_keys="Unit.DistrictID")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<District {self.DistrictID} {self.DistrictName!r}>"
