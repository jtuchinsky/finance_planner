from datetime import datetime
from pydantic import BaseModel, Field
from app.models.account import AccountType


class AccountCreate(BaseModel):
    """Schema for creating a new account"""

    name: str = Field(..., min_length=1, max_length=255)
    account_type: AccountType
    initial_balance: float = Field(default=0.00, ge=0)


class AccountUpdate(BaseModel):
    """Schema for updating an account"""

    name: str | None = Field(None, min_length=1, max_length=255)
    account_type: AccountType | None = None


class AccountResponse(BaseModel):
    """Schema for account response"""

    id: int
    user_id: int
    name: str
    account_type: AccountType
    balance: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AccountListResponse(BaseModel):
    """Schema for list of accounts"""

    accounts: list[AccountResponse]
    total: int