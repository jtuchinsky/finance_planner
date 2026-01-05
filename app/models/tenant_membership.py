"""Tenant membership model linking users to tenants with roles."""

from sqlalchemy import Integer, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from app.models.base import Base, TimestampMixin
from app.models.role import TenantRole

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.tenant import Tenant


class TenantMembership(Base, TimestampMixin):
    """
    Join table linking users to tenants with roles.

    This model enables:
    - Multiple users per tenant (family/household sharing)
    - One user can belong to multiple tenants (future feature)
    - Each user has exactly one role per tenant

    Example memberships:
    - User "Alice" has role OWNER in tenant "Smith Family"
    - User "Bob" has role MEMBER in tenant "Smith Family"
    - User "Alice" has role OWNER in tenant "Personal - Alice" (different tenant)

    Constraints:
    - Unique(tenant_id, user_id) - one membership per user per tenant
    - Each tenant must have exactly one OWNER (enforced at application layer)
    """

    __tablename__ = "tenant_memberships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[TenantRole] = mapped_column(
        Enum(TenantRole, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=TenantRole.MEMBER,
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="memberships")
    user: Mapped["User"] = relationship("User", back_populates="memberships")

    # Constraints
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user"),
    )

    def __repr__(self) -> str:
        return f"<TenantMembership(tenant_id={self.tenant_id}, user_id={self.user_id}, role={self.role.value})>"