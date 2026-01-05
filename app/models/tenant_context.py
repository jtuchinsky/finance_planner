"""Tenant context for request authorization."""

from dataclasses import dataclass
from app.models.user import User
from app.models.tenant import Tenant
from app.models.role import TenantRole


@dataclass
class TenantContext:
    """
    Complete tenant context for request authorization.

    Contains user, tenant, and role information extracted from JWT
    and verified against database. Used throughout the application
    for permission checks and tenant isolation.

    Attributes:
        user: The authenticated User object
        tenant: The Tenant the user is accessing
        role: The user's role within this tenant
    """

    user: User
    tenant: Tenant
    role: TenantRole

    def has_permission(self, required_role: TenantRole) -> bool:
        """
        Check if user's role meets or exceeds required role.

        Role hierarchy: OWNER (4) > ADMIN (3) > MEMBER (2) > VIEWER (1)

        Args:
            required_role: Minimum role required for the operation

        Returns:
            True if user has sufficient permissions
        """
        role_hierarchy = {
            TenantRole.OWNER: 4,
            TenantRole.ADMIN: 3,
            TenantRole.MEMBER: 2,
            TenantRole.VIEWER: 1,
        }
        return role_hierarchy[self.role] >= role_hierarchy[required_role]

    def is_owner(self) -> bool:
        """Check if user is the tenant owner."""
        return self.role == TenantRole.OWNER

    def is_admin_or_higher(self) -> bool:
        """Check if user is admin or owner."""
        return self.role in (TenantRole.OWNER, TenantRole.ADMIN)

    def can_write(self) -> bool:
        """Check if user has write permissions (MEMBER or higher)."""
        return self.role in (TenantRole.OWNER, TenantRole.ADMIN, TenantRole.MEMBER)

    def can_read(self) -> bool:
        """Check if user has read permissions (all roles can read)."""
        return True

    def __repr__(self) -> str:
        return f"<TenantContext(user_id={self.user.id}, tenant_id={self.tenant.id}, role={self.role.value})>"