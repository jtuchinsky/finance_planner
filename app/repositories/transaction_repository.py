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

    def create_bulk(self, transactions: list[Transaction]) -> list[Transaction]:
        """
        Create multiple transactions without committing.
        Caller responsible for commit. Enables atomic batch operations.
        """
        self.db.add_all(transactions)
        self.db.flush()  # Assign IDs without committing
        return transactions

    def create_no_commit(self, transaction: Transaction) -> Transaction:
        """Create single transaction without committing (for atomic ops)"""
        self.db.add(transaction)
        self.db.flush()
        return transaction

    def get_by_id(self, transaction_id: int) -> Optional[Transaction]:
        """Get transaction by ID"""
        return self.db.query(Transaction).filter(Transaction.id == transaction_id).first()

    def get_by_id_and_tenant(
        self, transaction_id: int, tenant_id: int
    ) -> Optional[Transaction]:
        """
        Get transaction by ID, ensuring it belongs to the tenant.
        Joins with Account to verify tenant ownership.

        Args:
            transaction_id: Transaction ID
            tenant_id: Tenant ID

        Returns:
            Transaction object or None if not found or belongs to different tenant
        """
        return (
            self.db.query(Transaction)
            .join(Account)
            .filter(
                Transaction.id == transaction_id,
                Account.tenant_id == tenant_id,
            )
            .first()
        )

    # DEPRECATED - Will be removed in Phase 8
    def get_by_id_and_user(
        self, transaction_id: int, user_id: int
    ) -> Optional[Transaction]:
        """DEPRECATED: Use get_by_id_and_tenant instead"""
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
        tenant_id: int,
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

        Args:
            tenant_id: Tenant ID for isolation
            account_id: Optional account filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            category: Optional category filter
            merchant: Optional merchant filter (case-insensitive partial match)
            tags: Optional list of tags to filter by (ANY match)
            der_category: Optional derived category filter
            der_merchant: Optional derived merchant filter (case-insensitive partial match)
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            Tuple of (transactions list, total count)
        """
        # Base query with tenant isolation via account join
        query = self.db.query(Transaction).join(Account).filter(Account.tenant_id == tenant_id)

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
