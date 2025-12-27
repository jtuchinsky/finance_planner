from datetime import date
from typing import Optional
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.models.account import Account
from app.models.user import User
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.account_repository import AccountRepository
from app.schemas.transaction_schemas import TransactionCreate, TransactionUpdate
from app.core.exceptions import NotFoundException, ForbiddenException


class TransactionService:
    """Service layer for transaction business logic"""

    def __init__(self, db: Session):
        self.db = db
        self.transaction_repo = TransactionRepository(db)
        self.account_repo = AccountRepository(db)

    def create_transaction(
        self, transaction_data: TransactionCreate, user: User
    ) -> Transaction:
        """
        Create a new transaction and update account balance atomically.

        Args:
            transaction_data: Transaction creation data
            user: Current user (for ownership verification)

        Returns:
            Created transaction

        Raises:
            NotFoundException: If account doesn't exist
            ForbiddenException: If account doesn't belong to user
        """
        # Verify account exists and belongs to user
        account = self.account_repo.get_by_id_and_user(
            transaction_data.account_id, user.id
        )
        if not account:
            raise NotFoundException(
                f"Account {transaction_data.account_id} not found or access denied"
            )

        # Create transaction
        transaction = Transaction(
            account_id=transaction_data.account_id,
            amount=transaction_data.amount,
            date=transaction_data.date,
            category=transaction_data.category,
            description=transaction_data.description,
            merchant=transaction_data.merchant,
            location=transaction_data.location,
            tags=transaction_data.tags if transaction_data.tags else [],
        )

        transaction = self.transaction_repo.create(transaction)

        # Update account balance atomically (within same DB transaction)
        account.balance = float(account.balance) + transaction_data.amount
        self.account_repo.update(account)

        return transaction

    def get_transaction(self, transaction_id: int, user: User) -> Transaction:
        """
        Get transaction by ID with ownership verification.

        Args:
            transaction_id: Transaction ID
            user: Current user

        Returns:
            Transaction

        Raises:
            NotFoundException: If transaction doesn't exist or doesn't belong to user
        """
        transaction = self.transaction_repo.get_by_id_and_user(transaction_id, user.id)
        if not transaction:
            raise NotFoundException(f"Transaction {transaction_id} not found")
        return transaction

    def get_transactions(
        self,
        user: User,
        account_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category: Optional[str] = None,
        merchant: Optional[str] = None,
        tags: Optional[list[str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Transaction], int]:
        """
        Get transactions with filters.

        Args:
            user: Current user
            account_id: Filter by account ID
            start_date: Filter by start date (inclusive)
            end_date: Filter by end date (inclusive)
            category: Filter by category
            merchant: Filter by merchant (partial match)
            tags: Filter by tags (any match)
            limit: Max results to return
            offset: Pagination offset

        Returns:
            Tuple of (transactions, total_count)
        """
        # If account_id provided, verify ownership
        if account_id is not None:
            account = self.account_repo.get_by_id_and_user(account_id, user.id)
            if not account:
                raise NotFoundException(
                    f"Account {account_id} not found or access denied"
                )

        return self.transaction_repo.get_with_filters(
            user_id=user.id,
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
            category=category,
            merchant=merchant,
            tags=tags,
            limit=limit,
            offset=offset,
        )

    def update_transaction(
        self, transaction_id: int, transaction_data: TransactionUpdate, user: User
    ) -> Transaction:
        """
        Update transaction and recalculate account balance if amount changed.

        Args:
            transaction_id: Transaction ID
            transaction_data: Updated transaction data
            user: Current user

        Returns:
            Updated transaction

        Raises:
            NotFoundException: If transaction doesn't exist or doesn't belong to user
        """
        # Get existing transaction with ownership verification
        transaction = self.transaction_repo.get_by_id_and_user(transaction_id, user.id)
        if not transaction:
            raise NotFoundException(f"Transaction {transaction_id} not found")

        # Track old amount for balance recalculation
        old_amount = transaction.amount

        # Update fields
        if transaction_data.amount is not None:
            transaction.amount = transaction_data.amount
        if transaction_data.date is not None:
            transaction.date = transaction_data.date
        if transaction_data.category is not None:
            transaction.category = transaction_data.category
        if transaction_data.description is not None:
            transaction.description = transaction_data.description
        if transaction_data.merchant is not None:
            transaction.merchant = transaction_data.merchant
        if transaction_data.location is not None:
            transaction.location = transaction_data.location
        if transaction_data.tags is not None:
            transaction.tags = transaction_data.tags

        transaction = self.transaction_repo.update(transaction)

        # Recalculate account balance if amount changed
        if transaction_data.amount is not None and old_amount != transaction.amount:
            account = self.account_repo.get_by_id(transaction.account_id)
            if account:
                # Remove old amount and add new amount
                account.balance = float(account.balance) - old_amount + transaction.amount
                self.account_repo.update(account)

        return transaction

    def delete_transaction(self, transaction_id: int, user: User) -> None:
        """
        Delete transaction and update account balance.

        Args:
            transaction_id: Transaction ID
            user: Current user

        Raises:
            NotFoundException: If transaction doesn't exist or doesn't belong to user
        """
        # Get existing transaction with ownership verification
        transaction = self.transaction_repo.get_by_id_and_user(transaction_id, user.id)
        if not transaction:
            raise NotFoundException(f"Transaction {transaction_id} not found")

        # Get account for balance update
        account = self.account_repo.get_by_id(transaction.account_id)

        # Delete transaction
        self.transaction_repo.delete(transaction)

        # Update account balance (subtract transaction amount)
        if account:
            account.balance = float(account.balance) - transaction.amount
            self.account_repo.update(account)
