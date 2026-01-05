from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_tenant_context
from app.models.tenant_context import TenantContext
from app.services.tenant_service import TenantService
from app.schemas.tenant_schemas import (
    TenantResponse,
    TenantUpdate,
    TenantMemberResponse,
    TenantInviteRequest,
    TenantRoleUpdate,
    TenantMemberRemoveResponse,
)

router = APIRouter()


@router.get("/me", response_model=TenantResponse)
async def get_current_tenant(
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Get current tenant details.

    Returns tenant information for the authenticated user's current tenant.
    """
    service = TenantService(db)
    return service.get_current_tenant(context)


@router.patch("/me", response_model=TenantResponse)
async def update_tenant(
    tenant_update: TenantUpdate,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Update tenant name.

    - **Requires OWNER permissions**
    - Only tenant name can be updated via this endpoint
    """
    service = TenantService(db)
    return service.update_tenant(tenant_update, context)


@router.get("/me/members", response_model=list[TenantMemberResponse])
async def list_members(
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    List all members of current tenant.

    Returns list of members with their roles and user information.
    Available to all authenticated members.
    """
    service = TenantService(db)
    return service.get_members(context)


@router.post(
    "/me/members",
    response_model=TenantMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def invite_member(
    invite_request: TenantInviteRequest,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Invite new member to tenant.

    - **Requires ADMIN or OWNER permissions**
    - Default role: MEMBER
    - Only OWNER can invite as OWNER
    - User will be auto-created if doesn't exist
    """
    service = TenantService(db)
    membership = service.invite_member(invite_request, context)

    # Get user info for response
    user = db.query(context.user.__class__).filter_by(id=membership.user_id).first()

    return {
        "id": membership.id,
        "user_id": membership.user_id,
        "auth_user_id": user.auth_user_id,
        "role": membership.role,
        "created_at": membership.created_at,
    }


@router.patch("/me/members/{user_id}/role", response_model=TenantMemberResponse)
async def update_member_role(
    user_id: int,
    role_update: TenantRoleUpdate,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Update member's role.

    - **Requires OWNER permissions**
    - Cannot change OWNER's role
    - Cannot change your own role
    """
    service = TenantService(db)
    membership = service.update_member_role(user_id, role_update, context)

    # Get user info for response
    user = db.query(context.user.__class__).filter_by(id=membership.user_id).first()

    return {
        "id": membership.id,
        "user_id": membership.user_id,
        "auth_user_id": user.auth_user_id,
        "role": membership.role,
        "created_at": membership.created_at,
    }


@router.delete(
    "/me/members/{user_id}",
    response_model=TenantMemberRemoveResponse,
    status_code=status.HTTP_200_OK,
)
async def remove_member(
    user_id: int,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Remove member from tenant.

    - **Requires ADMIN or OWNER permissions**
    - Cannot remove OWNER
    - Cannot remove yourself
    """
    service = TenantService(db)
    service.remove_member(user_id, context)

    return {
        "message": "Member removed successfully",
        "removed_user_id": user_id,
    }
