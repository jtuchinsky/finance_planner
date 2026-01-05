"""Repository for TenantMembership model operations."""

from sqlalchemy.orm import Session
from app.models.tenant_membership import TenantMembership
from app.models.role import TenantRole


class TenantMembershipRepository:
    """Repository for TenantMembership model operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_membership(self, user_id: int, tenant_id: int) -> TenantMembership | None:
        """
        Get membership for a specific user in a specific tenant.

        Args:
            user_id: User ID
            tenant_id: Tenant ID

        Returns:
            TenantMembership object or None if not found
        """
        return (
            self.db.query(TenantMembership)
            .filter(
                TenantMembership.user_id == user_id,
                TenantMembership.tenant_id == tenant_id,
            )
            .first()
        )

    def get_tenant_members(self, tenant_id: int) -> list[TenantMembership]:
        """
        Get all memberships for a tenant.

        Args:
            tenant_id: Tenant ID

        Returns:
            List of TenantMembership objects for the tenant
        """
        return (
            self.db.query(TenantMembership)
            .filter(TenantMembership.tenant_id == tenant_id)
            .all()
        )

    def get_user_memberships(self, user_id: int) -> list[TenantMembership]:
        """
        Get all memberships for a user (all tenants they belong to).

        Args:
            user_id: User ID

        Returns:
            List of TenantMembership objects for the user
        """
        return (
            self.db.query(TenantMembership)
            .filter(TenantMembership.user_id == user_id)
            .all()
        )

    def create(self, membership: TenantMembership) -> TenantMembership:
        """
        Create a new tenant membership.

        Args:
            membership: TenantMembership object to create

        Returns:
            Created TenantMembership object with ID populated

        Raises:
            IntegrityError: If (tenant_id, user_id) already exists
        """
        self.db.add(membership)
        self.db.commit()
        self.db.refresh(membership)
        return membership

    def update(self, membership: TenantMembership) -> TenantMembership:
        """
        Update a tenant membership.

        Args:
            membership: TenantMembership object to update

        Returns:
            Updated TenantMembership object
        """
        self.db.commit()
        self.db.refresh(membership)
        return membership

    def update_role(
        self, membership: TenantMembership, new_role: TenantRole
    ) -> TenantMembership:
        """
        Update a member's role.

        Args:
            membership: TenantMembership object to update
            new_role: New role to assign

        Returns:
            Updated TenantMembership object
        """
        membership.role = new_role
        self.db.commit()
        self.db.refresh(membership)
        return membership

    def delete(self, membership: TenantMembership) -> None:
        """
        Remove a user from a tenant.

        Args:
            membership: TenantMembership object to delete
        """
        self.db.delete(membership)
        self.db.commit()

    def get_owner(self, tenant_id: int) -> TenantMembership | None:
        """
        Get the owner membership for a tenant.

        Args:
            tenant_id: Tenant ID

        Returns:
            TenantMembership with OWNER role or None
        """
        return (
            self.db.query(TenantMembership)
            .filter(
                TenantMembership.tenant_id == tenant_id,
                TenantMembership.role == TenantRole.OWNER,
            )
            .first()
        )