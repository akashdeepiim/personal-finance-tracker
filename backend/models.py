from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text,
    ForeignKey,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=False)
    amount = Column(Numeric(18, 2), nullable=False)
    original_amount = Column(
        Numeric(18, 2), nullable=False
    )  # Original amount in original currency
    currency = Column(String(3), default="USD", nullable=False)
    description = Column(String(500), nullable=False)
    category = Column(String(100), nullable=True)
    subcategory = Column(String(100), nullable=True)
    account_type = Column(String, nullable=True)  # credit_card, bank_account
    transaction_type = Column(
        String, default="debit", nullable=False
    )  # debit (expense) or credit (income)
    statement_id = Column(Integer, ForeignKey("statements.id"), nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    statement = relationship("Statement", back_populates="transactions")


class Statement(Base):
    __tablename__ = "statements"
    __table_args__ = (
        UniqueConstraint("account_type", "file_hash", name="uq_statement_account_hash"),
    )

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    account_type = Column(String, nullable=False)
    currency = Column(
        String, default="USD", nullable=False
    )  # Default currency for statement
    file_hash = Column(String(64), nullable=True)
    upload_date = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)

    transactions = relationship(
        "Transaction", back_populates="statement", cascade="all, delete-orphan"
    )


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    __table_args__ = (UniqueConstraint("year", "month", name="uq_analysis_year_month"),)

    total_spending = Column(Numeric(18, 2), nullable=False)
    total_income = Column(Numeric(18, 2), default=0, nullable=False)
    category_breakdown = Column(Text, nullable=True)  # JSON string
    savings_recommendations = Column(Text, nullable=True)  # JSON string
    psychological_profile = Column(Text, nullable=True)  # JSON string
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class CategoryLearning(Base):
    __tablename__ = "category_learning"

    id = Column(Integer, primary_key=True, index=True)
    vendor_pattern = Column(String, nullable=False)  # Vendor/merchant name pattern
    description_pattern = Column(String, nullable=True)  # Description pattern
    category = Column(String, nullable=False)
    subcategory = Column(String, nullable=True)
    transaction_type = Column(
        String, default="debit", nullable=False
    )  # debit or credit
    confidence = Column(Float, default=1.0, nullable=False)  # Learning confidence score
    usage_count = Column(
        Integer, default=1, nullable=False
    )  # How many times this rule was used
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
