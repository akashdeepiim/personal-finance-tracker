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


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(320), nullable=False, unique=True, index=True)
    password_hash = Column(String(512), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    sessions = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship("User", back_populates="sessions")


class LoginThrottle(Base):
    __tablename__ = "login_throttles"

    id = Column(Integer, primary_key=True)
    identifier_hash = Column(String(64), nullable=False, unique=True, index=True)
    failure_count = Column(Integer, default=0, nullable=False)
    window_started_at = Column(DateTime(timezone=True), nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
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
        UniqueConstraint(
            "user_id",
            "account_type",
            "file_hash",
            name="uq_user_statement_account_hash",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
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
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    __table_args__ = (
        UniqueConstraint(
            "user_id", "year", "month", name="uq_user_analysis_year_month"
        ),
    )

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
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
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
