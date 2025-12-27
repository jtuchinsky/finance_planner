from datetime import date
from sqlalchemy import String, Integer, Numeric, ForeignKey, Date, Text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.account import Account


class Transaction(Base, TimestampMixin):
    """
    Financial transactions linked to accounts.

    Amount: Positive = income/deposit, Negative = expense/withdrawal
    Tags stored as JSON array for flexibility.
    """

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[float] = mapped_column(Numeric(precision=15, scale=2), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    merchant: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, default=list)

    # Relationships
    account: Mapped["Account"] = relationship("Account", back_populates="transactions")

    # Composite indexes for common queries
    __table_args__ = (
        Index("ix_transactions_account_date", "account_id", "date"),
        Index("ix_transactions_account_category", "account_id", "category"),
    )