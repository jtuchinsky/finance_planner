from jose import JWTError, jwt
from app.config import settings
from app.core.exceptions import UnauthorizedException


def decode_jwt(token: str) -> dict:
    """
    Decode and validate JWT token using shared SECRET_KEY.

    Args:
        token: JWT access token from Authorization header

    Returns:
        Decoded token payload with 'sub' (user_id), 'exp', etc.

    Raises:
        UnauthorizedException: If token invalid, expired, or malformed
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

        # Validate expiration (jose checks this automatically)
        exp = payload.get("exp")
        if exp is None:
            raise UnauthorizedException("Token missing expiration")

        # Extract user_id from 'sub' claim
        user_id: str = payload.get("sub")
        if user_id is None:
            raise UnauthorizedException("Token missing user identifier")

        return payload

    except JWTError as e:
        raise UnauthorizedException(f"Invalid token: {str(e)}")


def extract_user_id(token: str) -> str:
    """Extract auth_user_id from JWT token"""
    payload = decode_jwt(token)
    return payload["sub"]


def extract_tenant_id(token: str) -> str:
    """
    Extract tenant_id from JWT (provided by MCP_Auth).

    Args:
        token: JWT access token

    Returns:
        Tenant ID as string

    Raises:
        UnauthorizedException: If tenant_id claim missing
    """
    payload = decode_jwt(token)
    tenant_id = payload.get("tenant_id")
    if tenant_id is None:
        raise UnauthorizedException("Token missing tenant_id claim")
    return tenant_id


def extract_user_and_tenant(token: str) -> tuple[str, str]:
    """
    Extract both user_id and tenant_id from JWT.

    Args:
        token: JWT access token

    Returns:
        Tuple of (auth_user_id, tenant_id)

    Raises:
        UnauthorizedException: If either claim is missing
    """
    payload = decode_jwt(token)
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")

    if not user_id or not tenant_id:
        raise UnauthorizedException("Invalid token claims")

    return user_id, tenant_id