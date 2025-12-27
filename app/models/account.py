from enum import Enum as PyEnum
from sqlalchemy import String, Integer, Numeric, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.transaction import Transaction


class AccountType(str, PyEnum):
    """Account type enumeration"""

    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"
    INVESTMENT = "investment"
    LOAN = "loan"
    OTHER = "other"


class Account(Base, TimestampMixin):
    """
    Financial accounts owned by users.

    Balance is calculated field (sum of transactions) stored for performance.
    """

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,  # Critical for multi-tenant queries
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[AccountType] = mapped_column(
        Enum(AccountType, native_enum=False), nullable=False
    )
    balance: Mapped[float] = mapped_column(
        Numeric(precision=15, scale=2), nullable=False, default=0.00
    )
    # Balance updated via transaction service (not directly modified)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="accounts")
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        back_populates="account",
        cascade="all, delete-orphan",  # Delete transactions if account deleted
    )