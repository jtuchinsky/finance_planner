from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.security import extract_user_id
from app.core.exceptions import UnauthorizedException
from app.database import get_db
from app.repositories.user_repository import UserRepository
from app.models.user import User

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