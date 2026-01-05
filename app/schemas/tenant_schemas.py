from pydantic import BaseModel, Field
from datetime import datetime
from app.models.role import TenantRole


class TenantResponse(BaseModel):
    """Tenant details response"""

    id: int
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TenantUpdate(BaseModel):
    """Update tenant name (OWNER only)"""

    name: str = Field(..., min_length=1, max_length=255)


class TenantMemberResponse(BaseModel):
    """Tenant member details with user info"""

    id: int
    user_id: int
    auth_user_id: str  # From user.auth_user_id
    role: TenantRole
    created_at: datetime

    model_config = {"from_attributes": True}


class TenantInviteRequest(BaseModel):
    """Invite new member to tenant"""

    auth_user_id: str = Field(
        ..., description="MCP_Auth user ID to invite", min_length=1
    )
    role: TenantRole = Field(
        default=TenantRole.MEMBER, description="Role to assign (default: MEMBER)"
    )


class TenantRoleUpdate(BaseModel):
    """Update member's role (OWNER only)"""

    role: TenantRole = Field(..., description="New role to assign")


class TenantMemberRemoveResponse(BaseModel):
    """Response after removing member"""

    message: str
    removed_user_id: int
