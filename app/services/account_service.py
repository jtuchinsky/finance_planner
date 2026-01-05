from sqlalchemy.orm import Session
from app.models.account import Account
from app.models.user import User
from app.models.tenant_context import TenantContext
from app.repositories.account_repository import AccountRepository
from app.schemas.account_schemas import AccountCreate, AccountUpdate
from app.core.exceptions import NotFoundException, ForbiddenException


class AccountService:
    """Service for account business logic"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = AccountRepository(db)

    def create_account(self, data: AccountCreate, context: TenantContext) -> Account:
        """
        Create new account for tenant.

        Args:
            data: Account creation data
            context: Tenant context with user, tenant, and role

        Returns:
            Created Account object

        Raises:
            ForbiddenException: If user lacks write permissions (MEMBER or higher)
        """
        if not context.can_write():
            raise ForbiddenException("Insufficient permissions to create accounts")

        account = Account(
            tenant_id=context.tenant.id,
            user_id=context.user.id,  # Keep for Phase 8 cleanup
            name=data.name,
            account_type=data.account_type,
            balance=data.initial_balance or 0.00,
        )
        return self.repo.create(account)

    def get_tenant_accounts(self, context: TenantContext) -> list[Account]:
        """
        Get all accounts for tenant.

        Args:
            context: Tenant context

        Returns:
            List of Account objects for the tenant
        """
        return self.repo.get_by_tenant(context.tenant.id)

    def get_account(self, account_id: int, context: TenantContext) -> Account:
        """
        Get specific account ensuring tenant ownership.

        Args:
            account_id: Account ID
            context: Tenant context

        Returns:
            Account object

        Raises:
            NotFoundException: If account not found or belongs to another tenant
        """
        account = self.repo.get_by_id_and_tenant(account_id, context.tenant.id)
        if not account:
            raise NotFoundException("Account not found")
        return account

    def update_account(
        self, account_id: int, data: AccountUpdate, context: TenantContext
    ) -> Account:
        """
        Update account details.

        Args:
            account_id: Account ID
            data: Update data
            context: Tenant context

        Returns:
            Updated Account object

        Raises:
            NotFoundException: If account not found
            ForbiddenException: If user lacks write permissions
        """
        if not context.can_write():
            raise ForbiddenException("Insufficient permissions to update accounts")

        account = self.get_account(account_id, context)

        if data.name is not None:
            account.name = data.name
        if data.account_type is not None:
            account.account_type = data.account_type

        return self.repo.update(account)

    def delete_account(self, account_id: int, context: TenantContext) -> None:
        """
        Delete account and all transactions (cascade).

        Args:
            account_id: Account ID
            context: Tenant context

        Raises:
            NotFoundException: If account not found
            ForbiddenException: If user lacks write permissions
        """
        if not context.can_write():
            raise ForbiddenException("Insufficient permissions to delete accounts")

        account = self.get_account(account_id, context)
        self.repo.delete(account)

    # DEPRECATED - Will be removed in Phase 8
    def get_user_accounts(self, user: User) -> list[Account]:
        """DEPRECATED: Use get_tenant_accounts instead"""
        return self.repo.get_by_user(user.id)