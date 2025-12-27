from datetime import date, datetime
from pydantic import BaseModel, Field
from typing import Optional


class TransactionCreate(BaseModel):
    """Schema for creating a new transaction"""

    account_id: int = Field(..., gt=0)
    amount: float = Field(..., description="Positive for income, negative for expense")
    date: date
    category: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    merchant: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    tags: Optional[list[str]] = Field(default_factory=list)


class TransactionUpdate(BaseModel):
    """Schema for updating a transaction"""

    amount: Optional[float] = None
    date: Optional[date] = None
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    merchant: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    tags: Optional[list[str]] = None


class TransactionResponse(BaseModel):
    """Schema for transaction response"""

    model_config = {"from_attributes": True}

    id: int
    account_id: int
    amount: float
    date: date
    category: str
    description: Optional[str]
    merchant: Optional[str]
    location: Optional[str]
    tags: Optional[list[str]]
    created_at: datetime
    updated_at: datetime


class TransactionListResponse(BaseModel):
    """Schema for list of transactions"""

    transactions: list[TransactionResponse]
    total: int


class TransactionFilter(BaseModel):
    """Schema for filtering transactions"""

    account_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    category: Optional[str] = None
    merchant: Optional[str] = None
    tags: Optional[list[str]] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
