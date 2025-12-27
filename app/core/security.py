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