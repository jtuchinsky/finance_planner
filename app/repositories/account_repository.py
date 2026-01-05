from sqlalchemy.orm import Session
from app.models.account import Account


class AccountRepository:
    """Repository for Account model operations with multi-tenant support"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_tenant(self, tenant_id: int) -> list[Account]:
        """
        Get all accounts for a tenant.

        Args:
            tenant_id: Tenant ID

        Returns:
            List of Account objects for the tenant
        """
        return self.db.query(Account).filter(Account.tenant_id == tenant_id).all()

    def get_by_id_and_tenant(self, account_id: int, tenant_id: int) -> Account | None:
        """
        Get account ensuring it belongs to tenant (multi-tenant safety).

        Args:
            account_id: Account ID
            tenant_id: Tenant ID

        Returns:
            Account object or None if not found or belongs to different tenant
        """
        return (
            self.db.query(Account)
            .filter(Account.id == account_id, Account.tenant_id == tenant_id)
            .first()
        )

    # DEPRECATED - Will be removed in Phase 8
    def get_by_user(self, user_id: int) -> list[Account]:
        """DEPRECATED: Use get_by_tenant instead"""
        return self.db.query(Account).filter(Account.user_id == user_id).all()

    # DEPRECATED - Will be removed in Phase 8
    def get_by_id_and_user(self, account_id: int, user_id: int) -> Account | None:
        """DEPRECATED: Use get_by_id_and_tenant instead"""
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

    def update_no_commit(self, account: Account) -> Account:
        """Update account without committing. Caller responsible for commit."""
        self.db.flush()
        return account

    def delete(self, account: Account) -> None:
        """Delete account (cascades to transactions)"""
        self.db.delete(account)
        self.db.commit()