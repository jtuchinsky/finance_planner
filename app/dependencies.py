from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.security import extract_user_id, extract_user_and_tenant
from app.core.exceptions import UnauthorizedException
from app.database import get_db
from app.repositories.user_repository import UserRepository
from app.repositories.tenant_repository import TenantRepository
from app.repositories.tenant_membership_repository import TenantMembershipRepository
from app.models.user import User
from app.models.tenant_context import TenantContext

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency to validate JWT and get/create user.

    Flow:
    1. Extract token from Authorization: Bearer <token>
    2. Validate JWT using shared SECRET_KEY
    3. Extract auth_user_id from 'sub' claim
    4. Get or auto-create User record in finance DB
    5. Return User object for use in endpoints

    Raises:
        HTTPException 401: If token invalid or expired
    """
    try:
        token = credentials.credentials
        auth_user_id = extract_user_id(token)

        # Get or create user in finance tracker DB
        user_repo = UserRepository(db)
        user = user_repo.get_or_create_by_auth_id(auth_user_id)

        return user

    except UnauthorizedException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_tenant_context(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> TenantContext:
    """
    FastAPI dependency to validate JWT and build tenant context.

    Flow:
    1. Extract token from Authorization: Bearer <token>
    2. Validate JWT and extract user_id and tenant_id
    3. Get or auto-create User record
    4. Verify Tenant exists
    5. Verify User has membership in Tenant
    6. Return TenantContext with user, tenant, and role

    Raises:
        HTTPException 401: If token invalid or expired
        HTTPException 403: If user not member of tenant
        HTTPException 404: If tenant not found
    """
    try:
        token = credentials.credentials
        auth_user_id, tenant_id_str = extract_user_and_tenant(token)
        tenant_id = int(tenant_id_str)

        # Get or create user
        user_repo = UserRepository(db)
        user = user_repo.get_or_create_by_auth_id(auth_user_id)

        # Verify tenant exists
        tenant_repo = TenantRepository(db)
        tenant = tenant_repo.get_by_id(tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {tenant_id} not found",
            )

        # Verify user has membership in this tenant
        membership_repo = TenantMembershipRepository(db)
        membership = membership_repo.get_membership(user.id, tenant_id)
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User not member of tenant {tenant_id}",
            )

        return TenantContext(user=user, tenant=tenant, role=membership.role)

    except UnauthorizedException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except ValueError as e:
        # Handle int(tenant_id_str) conversion error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tenant_id: {str(e)}",
        )