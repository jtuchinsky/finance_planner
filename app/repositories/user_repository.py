from sqlalchemy.orm import Session
from app.models.user import User


class UserRepository:
    """Repository for User model operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_or_create_by_auth_id(self, auth_user_id: str) -> User:
        """
        Get user by auth_user_id or create if doesn't exist.

        This is called automatically when a user makes their first API
        request with a valid JWT from MCP_Auth.

        Args:
            auth_user_id: User ID from MCP_Auth JWT 'sub' claim

        Returns:
            User object (either existing or newly created)
        """
        user = self.db.query(User).filter(User.auth_user_id == auth_user_id).first()

        if not user:
            user = User(auth_user_id=auth_user_id)
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)

        return user

    def get_by_auth_id(self, auth_user_id: str) -> User | None:
        """Get user by auth_user_id"""
        return self.db.query(User).filter(User.auth_user_id == auth_user_id).first()

    def get_by_id(self, user_id: int) -> User | None:
        """Get user by internal ID"""
        return self.db.query(User).filter(User.id == user_id).first()