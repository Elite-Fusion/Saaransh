"""
SQLAlchemy ORM models — AI / Security extension group.

  - AuditLog   : every AI query logged for trust + compliance
  - Users      : RBAC; bound to an Employee record
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.session import Base

if TYPE_CHECKING:
    from backend.models.organisation import Employee


class AuditLog(Base):
    """One row per AI query — who, what, when, how many results."""

    __tablename__ = "AuditLog"

    LogID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    EmployeeID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Employee.EmployeeID"), nullable=True
    )
    officer_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    officer_rank: Mapped[str | None] = mapped_column(Text, nullable=True)
    action: Mapped[str | None] = mapped_column(String(50), nullable=True)
    query_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships ----------------------------------------------------------
    employee: Mapped["Employee | None"] = relationship(  # noqa: F821
        "Employee", foreign_keys=[EmployeeID]
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AuditLog {self.LogID} action={self.action!r}>"


class Users(Base):
    """A login identity bound to an Employee. Role drives RBAC later."""

    __tablename__ = "Users"

    UserID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    EmployeeID: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Employee.EmployeeID"), nullable=True
    )
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    is_active: Mapped[bool | None] = mapped_column(Boolean, default=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships ----------------------------------------------------------
    employee: Mapped["Employee | None"] = relationship(  # noqa: F821
        "Employee", foreign_keys=[EmployeeID]
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Users {self.UserID} {self.email!r} role={self.role!r}>"
