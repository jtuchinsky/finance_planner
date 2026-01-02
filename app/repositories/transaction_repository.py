from datetime import date
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.transaction import Transaction
from app.models.account import Account


class TransactionRepository:
    """Repository for Transaction data access"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, transaction: Transaction) -> Transaction:
        """Create a new transaction"""
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def get_by_id(self, transaction_id: int) -> Optional[Transaction]:
        """Get transaction by ID"""
        return self.db.query(Transaction).filter(Transaction.id == transaction_id).first()

    def get_by_id_and_user(
        self, transaction_id: int, user_id: int
    ) -> Optional[Transaction]:
        """
        Get transaction by ID, ensuring it belongs to the user.
        Joins with Account to verify ownership.
        """
        return (
            self.db.query(Transaction)
            .join(Account)
            .filter(
                Transaction.id == transaction_id,
                Account.user_id == user_id,
            )
            .first()
        )

    def get_by_account(self, account_id: int, limit: int = 100, offset: int = 0) -> list[Transaction]:
        """Get all transactions for an account with pagination"""
        return (
            self.db.query(Transaction)
            .filter(Transaction.account_id == account_id)
            .order_by(Transaction.date.desc(), Transaction.id.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    def get_with_filters(
        self,
        user_id: int,
        account_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category: Optional[str] = None,
        merchant: Optional[str] = None,
        tags: Optional[list[str]] = None,
        der_category: Optional[str] = None,
        der_merchant: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Transaction], int]:
        """
        Get transactions with filters, ensuring multi-tenant isolation.
        Returns (transactions, total_count).
        """
        # Base query with user isolation via account join
        query = self.db.query(Transaction).join(Account).filter(Account.user_id == user_id)

        # Apply filters
        if account_id is not None:
            query = query.filter(Transaction.account_id == account_id)

        if start_date is not None:
            query = query.filter(Transaction.date >= start_date)

        if end_date is not None:
            query = query.filter(Transaction.date <= end_date)

        if category is not None:
            query = query.filter(Transaction.category == category)

        if merchant is not None:
            query = query.filter(Transaction.merchant.ilike(f"%{merchant}%"))

        if der_category is not None:
            query = query.filter(Transaction.der_category == der_category)

        if der_merchant is not None:
            query = query.filter(Transaction.der_merchant.ilike(f"%{der_merchant}%"))

        if tags is not None and len(tags) > 0:
            # Filter for transactions that have ANY of the provided tags
            # SQLite doesn't have native JSON operators, so we'll use LIKE
            # In production with PostgreSQL, we'd use @> operator
            tag_filters = [Transaction.tags.contains(tag) for tag in tags]
            query = query.filter(or_(*tag_filters))

        # Get total count before pagination
        total = query.count()

        # Apply sorting and pagination
        transactions = (
            query.order_by(Transaction.date.desc(), Transaction.id.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

        return transactions, total

    def update(self, transaction: Transaction) -> Transaction:
        """Update a transaction"""
        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def delete(self, transaction: Transaction) -> None:
        """Delete a transaction"""
        self.db.delete(transaction)
        self.db.commit()

    def get_account_balance(self, account_id: int) -> float:
        """Calculate account balance from all transactions"""
        from sqlalchemy import func

        result = (
            self.db.query(func.sum(Transaction.amount))
            .filter(Transaction.account_id == account_id)
            .scalar()
        )
        return float(result) if result is not None else 0.0
