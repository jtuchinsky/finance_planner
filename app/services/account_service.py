from sqlalchemy.orm import Session
from app.models.account import Account
from app.models.user import User
from app.repositories.account_repository import AccountRepository
from app.schemas.account_schemas import AccountCreate, AccountUpdate
from app.core.exceptions import NotFoundException


class AccountService:
    """Service for account business logic"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = AccountRepository(db)

    def create_account(self, data: AccountCreate, user: User) -> Account:
        """Create new account for user"""
        account = Account(
            user_id=user.id,
            name=data.name,
            account_type=data.account_type,
            balance=data.initial_balance or 0.00,
        )
        return self.repo.create(account)

    def get_user_accounts(self, user: User) -> list[Account]:
        """Get all accounts for user"""
        return self.repo.get_by_user(user.id)

    def get_account(self, account_id: int, user: User) -> Account:
        """
        Get specific account ensuring user ownership.

        Raises:
            NotFoundException: If account not found or belongs to another user
        """
        account = self.repo.get_by_id_and_user(account_id, user.id)
        if not account:
            raise NotFoundException("Account not found")
        return account

    def update_account(self, account_id: int, data: AccountUpdate, user: User) -> Account:
        """Update account details"""
        account = self.get_account(account_id, user)

        if data.name is not None:
            account.name = data.name
        if data.account_type is not None:
            account.account_type = data.account_type

        return self.repo.update(account)

    def delete_account(self, account_id: int, user: User) -> None:
        """Delete account and all transactions (cascade)"""
        account = self.get_account(account_id, user)
        self.repo.delete(account)