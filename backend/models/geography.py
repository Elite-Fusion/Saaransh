"""
SQLAlchemy ORM models — Geography group.

Tables with no dependencies on other tables in the schema:
  - State
  - District
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.session import Base

if TYPE_CHECKING:
    from backend.models.organisation import Court, Unit


class State(Base):
    """A state in India. Seed currently only has Karnataka (id=1)."""

    __tablename__ = "State"

    StateID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    StateName: Mapped[str] = mapped_column(String(100), nullable=False)
    NationalityID: Mapped[int | None] = mapped_column(Integer, nullable=True)
    Active: Mapped[bool | None] = mapped_column(Boolean, default=True)

    # Relationships ----------------------------------------------------------
    # A state has many districts and many units.
    districts: Mapped[list["District"]] = relationship(
        back_populates="state",
        cascade="save-update, merge",
    )
    units: Mapped[list["Unit"]] = relationship(
        back_populates="state",
        cascade="save-update, merge",
        foreign_keys="Unit.StateID",
    )
    courts: Mapped[list["Court"]] = relationship(
        back_populates="state",
        cascade="save-update, merge",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<State {self.StateID} {self.StateName!r}>"


class District(Base):
    """A police district within a state. Seed has 8 Karnataka districts."""

    __tablename__ = "District"

    DistrictID: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    DistrictName: Mapped[str] = mapped_column(String(100), nullable=False)
    StateID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("State.StateID"), nullable=True
    )
    Active: Mapped[bool | None] = mapped_column(Boolean, default=True)

    # Relationships ----------------------------------------------------------
    state: Mapped["State | None"] = relationship(back_populates="districts")
    units: Mapped[list["Unit"]] = relationship(
        back_populates="district",
        cascade="save-update, merge",
        foreign_keys="Unit.DistrictID",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<District {self.DistrictID} {self.DistrictName!r}>"
