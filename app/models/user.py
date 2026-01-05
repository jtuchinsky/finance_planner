from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.tenant_membership import TenantMembership


class User(Base, TimestampMixin):
    """
    Tracks users from MCP_Auth service.

    Only stores user_id (sub from JWT) - no auth credentials.
    Auto-created on first API request with valid JWT.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    auth_user_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    # auth_user_id is the 'sub' claim from JWT (MCP_Auth user ID)

    # Relationships
    accounts: Mapped[list["Account"]] = relationship(
        "Account",
        back_populates="user",
        cascade="all, delete-orphan",  # Delete accounts if user deleted
        # NOTE: Will be removed in Phase 8 after migration complete
    )
    memberships: Mapped[list["TenantMembership"]] = relationship(
        "TenantMembership",
        back_populates="user",
        cascade="all, delete-orphan",
    )