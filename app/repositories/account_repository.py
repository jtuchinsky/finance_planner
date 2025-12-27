from sqlalchemy.orm import Session
from app.models.account import Account


class AccountRepository:
    """Repository for Account model operations with multi-tenant support"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_user(self, user_id: int) -> list[Account]:
        """Get all accounts for a user"""
        return self.db.query(Account).filter(Account.user_id == user_id).all()

    def get_by_id_and_user(self, account_id: int, user_id: int) -> Account | None:
        """
        Get account ensuring it belongs to user (multi-tenant safety).

        Returns None if account doesn't exist or belongs to another user.
        """
        return (
            self.db.query(Account)
            .filter(Account.id == account_id, Account.user_id == user_id)
            .first()
        )

    def create(self, account: Account) -> Account:
        """Create new account"""
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def update(self, account: Account) -> Account:
        """Update existing account"""
        self.db.commit()
        self.db.refresh(account)
        return account

    def delete(self, account: Account) -> None:
        """Delete account (cascades to transactions)"""
        self.db.delete(account)
        self.db.commit()