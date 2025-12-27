from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.account_service import AccountService
from app.schemas.account_schemas import (
    AccountCreate,
    AccountUpdate,
    AccountResponse,
    AccountListResponse,
)

router = APIRouter()


@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    data: AccountCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Create a new account for the authenticated user"""
    service = AccountService(db)
    account = service.create_account(data, user)
    return account


@router.get("/", response_model=AccountListResponse)
async def list_accounts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all accounts for the authenticated user"""
    service = AccountService(db)
    accounts = service.get_user_accounts(user)
    return AccountListResponse(accounts=accounts, total=len(accounts))


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get specific account details"""
    service = AccountService(db)
    account = service.get_account(account_id, user)
    return account


@router.patch("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: int,
    data: AccountUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update account details"""
    service = AccountService(db)
    account = service.update_account(account_id, data, user)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Delete account and all associated transactions"""
    service = AccountService(db)
    service.delete_account(account_id, user)
    return None