from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_tenant_context
from app.models.tenant_context import TenantContext
from app.services.transaction_service import TransactionService
from app.schemas.transaction_schemas import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionListResponse,
    TransactionBatchCreate,
    TransactionBatchResponse,
)

router = APIRouter()


@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    transaction_data: TransactionCreate,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Create a new transaction.

    - Updates account balance automatically
    - Requires valid account_id owned by tenant
    - Amount: positive for income/deposits, negative for expenses/withdrawals
    - Requires MEMBER or higher permissions
    """
    service = TransactionService(db)
    return service.create_transaction(transaction_data, context)


@router.post("/batch", response_model=TransactionBatchResponse, status_code=status.HTTP_201_CREATED)
def create_transaction_batch(
    batch_data: TransactionBatchCreate,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Create multiple transactions atomically for a single account.

    - All transactions succeed or entire batch is rolled back
    - Minimum 1, maximum 100 transactions per batch
    - Updates account balance exactly once
    - All transactions share the same account_id
    - Requires MEMBER or higher permissions
    """
    service = TransactionService(db)
    transactions, balance = service.create_transaction_batch(batch_data, context)

    total_amount = sum(txn.amount for txn in transactions)

    return TransactionBatchResponse(
        transactions=transactions,
        account_balance=balance,
        total_amount=total_amount,
        count=len(transactions),
    )


@router.get("/", response_model=TransactionListResponse)
def list_transactions(
    account_id: Optional[int] = Query(None, description="Filter by account ID"),
    start_date: Optional[date] = Query(None, description="Start date (inclusive)"),
    end_date: Optional[date] = Query(None, description="End date (inclusive)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    merchant: Optional[str] = Query(None, description="Filter by merchant (partial match)"),
    tags: Optional[str] = Query(
        None, description="Comma-separated list of tags (matches ANY)"
    ),
    der_category: Optional[str] = Query(None, description="Filter by derived category"),
    der_merchant: Optional[str] = Query(None, description="Filter by derived merchant (partial match)"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    List transactions with optional filters.

    - Returns only transactions from accounts owned by the tenant
    - Supports filtering by account, date range, category, merchant, tags
    - Results sorted by date (newest first)
    """
    service = TransactionService(db)

    # Parse comma-separated tags
    tags_list = [tag.strip() for tag in tags.split(",")] if tags else None

    transactions, total = service.get_transactions(
        context=context,
        account_id=account_id,
        start_date=start_date,
        end_date=end_date,
        category=category,
        merchant=merchant,
        tags=tags_list,
        der_category=der_category,
        der_merchant=der_merchant,
        limit=limit,
        offset=offset,
    )

    return TransactionListResponse(transactions=transactions, total=total)


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: int,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Get a specific transaction by ID.

    - Returns 404 if transaction doesn't exist or doesn't belong to tenant
    """
    service = TransactionService(db)
    return service.get_transaction(transaction_id, context)


@router.patch("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: int,
    transaction_data: TransactionUpdate,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Update a transaction.

    - Automatically recalculates account balance if amount changed
    - Returns 404 if transaction doesn't exist or doesn't belong to tenant
    - Only provided fields are updated (partial update)
    - Requires MEMBER or higher permissions
    """
    service = TransactionService(db)
    return service.update_transaction(transaction_id, transaction_data, context)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Delete a transaction.

    - Automatically updates account balance
    - Returns 404 if transaction doesn't exist or doesn't belong to tenant
    - Requires MEMBER or higher permissions
    """
    service = TransactionService(db)
    service.delete_transaction(transaction_id, context)
