from sqlalchemy.orm import Session
from app.models.tenant import Tenant
from app.models.tenant_membership import TenantMembership
from app.models.user import User
from app.models.tenant_context import TenantContext
from app.models.role import TenantRole
from app.repositories.tenant_repository import TenantRepository
from app.repositories.tenant_membership_repository import TenantMembershipRepository
from app.repositories.user_repository import UserRepository
from app.schemas.tenant_schemas import (
    TenantUpdate,
    TenantInviteRequest,
    TenantRoleUpdate,
)
from app.core.exceptions import (
    NotFoundException,
    ForbiddenException,
    ValidationException,
)


class TenantService:
    """Service layer for tenant management business logic"""

    def __init__(self, db: Session):
        self.db = db
        self.tenant_repo = TenantRepository(db)
        self.membership_repo = TenantMembershipRepository(db)
        self.user_repo = UserRepository(db)

    def list_user_tenants(self, user: User) -> list[dict]:
        """
        List all tenants that a user belongs to.

        Args:
            user: Authenticated user

        Returns:
            List of tenants with user's role in each tenant
        """
        memberships = self.membership_repo.get_user_memberships(user.id)

        result = []
        for membership in memberships:
            tenant = self.tenant_repo.get_by_id(membership.tenant_id)
            if tenant:
                result.append(
                    {
                        "id": tenant.id,
                        "name": tenant.name,
                        "role": membership.role,
                        "created_at": tenant.created_at,
                        "updated_at": tenant.updated_at,
                    }
                )
        return result

    def get_current_tenant(self, context: TenantContext) -> Tenant:
        """
        Get current tenant details.

        Args:
            context: Tenant context with authenticated user

        Returns:
            Current tenant object
        """
        return context.tenant

    def update_tenant(
        self, tenant_update: TenantUpdate, context: TenantContext
    ) -> Tenant:
        """
        Update tenant name (OWNER only).

        Args:
            tenant_update: New tenant name
            context: Tenant context

        Returns:
            Updated tenant

        Raises:
            ForbiddenException: If user is not OWNER
        """
        if not context.is_owner():
            raise ForbiddenException("Only owner can update tenant details")

        context.tenant.name = tenant_update.name
        return self.tenant_repo.update(context.tenant)

    def get_members(self, context: TenantContext) -> list[dict]:
        """
        Get all members of current tenant with user details.

        Args:
            context: Tenant context

        Returns:
            List of members with user info
        """
        memberships = self.membership_repo.get_tenant_members(context.tenant.id)

        # Enrich with user auth_user_id
        result = []
        for membership in memberships:
            user = self.user_repo.get_by_id(membership.user_id)
            result.append(
                {
                    "id": membership.id,
                    "user_id": membership.user_id,
                    "auth_user_id": user.auth_user_id if user else "unknown",
                    "role": membership.role,
                    "created_at": membership.created_at,
                }
            )
        return result

    def invite_member(
        self, invite_request: TenantInviteRequest, context: TenantContext
    ) -> TenantMembership:
        """
        Invite new member to tenant (ADMIN or OWNER).

        Args:
            invite_request: Invite details with auth_user_id and role
            context: Tenant context

        Returns:
            Created membership

        Raises:
            ForbiddenException: If user lacks admin permissions
            ValidationException: If user is already a member
        """
        if not context.is_admin_or_higher():
            raise ForbiddenException("Only admins and owners can invite members")

        # Get or create user by auth_user_id
        user = self.user_repo.get_or_create_by_auth_id(invite_request.auth_user_id)

        # Check if already a member
        existing = self.membership_repo.get_membership(user.id, context.tenant.id)
        if existing:
            raise ValidationException(
                f"User {invite_request.auth_user_id} is already a member"
            )

        # ADMINs cannot invite as OWNER
        if invite_request.role == TenantRole.OWNER and not context.is_owner():
            raise ForbiddenException("Only owner can invite other owners")

        # Create membership
        membership = TenantMembership(
            tenant_id=context.tenant.id,
            user_id=user.id,
            role=invite_request.role,
        )
        return self.membership_repo.create(membership)

    def update_member_role(
        self, user_id: int, role_update: TenantRoleUpdate, context: TenantContext
    ) -> TenantMembership:
        """
        Update member's role (OWNER only).

        Args:
            user_id: User ID to update
            role_update: New role
            context: Tenant context

        Returns:
            Updated membership

        Raises:
            ForbiddenException: If user is not OWNER or trying to change owner
            NotFoundException: If membership not found
        """
        if not context.is_owner():
            raise ForbiddenException("Only owner can change member roles")

        # Get membership
        membership = self.membership_repo.get_membership(user_id, context.tenant.id)
        if not membership:
            raise NotFoundException("Member not found in this tenant")

        # Cannot modify self (check first for better error message)
        if user_id == context.user.id:
            raise ForbiddenException("Cannot change your own role")

        # Cannot change OWNER role
        if membership.role == TenantRole.OWNER:
            raise ForbiddenException("Cannot change owner's role")

        # Update role
        membership.role = role_update.role
        return self.membership_repo.update(membership)

    def remove_member(self, user_id: int, context: TenantContext) -> None:
        """
        Remove member from tenant (ADMIN or OWNER).

        Args:
            user_id: User ID to remove
            context: Tenant context

        Raises:
            ForbiddenException: If user lacks permissions or trying to remove owner
            NotFoundException: If membership not found
        """
        if not context.is_admin_or_higher():
            raise ForbiddenException("Only admins and owners can remove members")

        # Get membership
        membership = self.membership_repo.get_membership(user_id, context.tenant.id)
        if not membership:
            raise NotFoundException("Member not found in this tenant")

        # Cannot remove self (check first for better error message)
        if user_id == context.user.id:
            raise ForbiddenException("Cannot remove yourself from tenant")

        # Cannot remove OWNER
        if membership.role == TenantRole.OWNER:
            raise ForbiddenException("Cannot remove owner from tenant")

        # Delete membership
        self.membership_repo.delete(membership)
