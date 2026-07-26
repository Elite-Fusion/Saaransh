"""
SQLAlchemy ORM models — AI / Security extension group.

Column names match the Supabase schema exactly (all lowercase).
Python attribute names are unchanged for backward compatibility.
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
    __tablename__ = "auditlog"

    LogID: Mapped[int] = mapped_column("logid", Integer, primary_key=True, autoincrement=True)
    EmployeeID: Mapped[int | None] = mapped_column("employeeid", Integer, ForeignKey("employee.employeeid"), nullable=True)
    officer_name: Mapped[str | None] = mapped_column("officer_name", Text, nullable=True)
    officer_rank: Mapped[str | None] = mapped_column("officer_rank", Text, nullable=True)
    action: Mapped[str | None] = mapped_column("action", String(50), nullable=True)
    query_text: Mapped[str | None] = mapped_column("query_text", Text, nullable=True)
    result_count: Mapped[int | None] = mapped_column("result_count", Integer, nullable=True)
    ip_address: Mapped[str | None] = mapped_column("ip_address", String(50), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column("created_at", DateTime, nullable=True)

    employee: Mapped["Employee | None"] = relationship("Employee", foreign_keys=[EmployeeID])

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AuditLog {self.LogID} action={self.action!r}>"


class Users(Base):
    __tablename__ = "users"

    UserID: Mapped[int] = mapped_column("userid", Integer, primary_key=True, autoincrement=True)
    EmployeeID: Mapped[int | None] = mapped_column("employeeid", Integer, ForeignKey("employee.employeeid"), nullable=True)
    name: Mapped[str | None] = mapped_column("name", String(150), nullable=True)
    email: Mapped[str] = mapped_column("email", Text, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column("password_hash", String(256), nullable=False)
    role: Mapped[str] = mapped_column("role", String(30), nullable=False)
    is_active: Mapped[bool | None] = mapped_column("is_active", Boolean, default=True)
    last_login: Mapped[datetime | None] = mapped_column("last_login", DateTime, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column("created_at", DateTime, nullable=True)

    employee: Mapped["Employee | None"] = relationship("Employee", foreign_keys=[EmployeeID])

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Users {self.UserID} {self.email!r} role={self.role!r}>"
