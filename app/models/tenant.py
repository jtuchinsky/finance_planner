"""Tenant model for multi-tenant isolation."""

from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.tenant_membership import TenantMembership
    from app.models.account import Account


class Tenant(Base, TimestampMixin):
    """
    Multi-tenant isolation boundary.

    A tenant represents a group of users who share financial data.
    This enables family/household sharing while maintaining strict
    isolation between different tenants.

    Examples:
    - "Smith Family" - household with multiple members
    - "Personal - John" - individual user's finances
    - "Acme Corp" - business entity

    All accounts, transactions, budgets, etc. belong to a tenant,
    not individual users. Users access tenant data through memberships
    with specific roles (Owner, Admin, Member, Viewer).
    """

    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships
    memberships: Mapped[list["TenantMembership"]] = relationship(
        "TenantMembership",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    accounts: Mapped[list["Account"]] = relationship(
        "Account",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name='{self.name}')>"