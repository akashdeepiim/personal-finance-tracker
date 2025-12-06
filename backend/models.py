from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=False)
    amount = Column(Float, nullable=False)
    original_amount = Column(Float, nullable=False)  # Original amount in original currency
    currency = Column(String, default="USD", nullable=False)  # Currency code (USD, EUR, GBP, etc.)
    description = Column(String, nullable=False)
    category = Column(String, nullable=True)
    subcategory = Column(String, nullable=True)
    account_type = Column(String, nullable=True)  # credit_card, bank_account
    transaction_type = Column(String, default="debit", nullable=False)  # debit (expense) or credit (income)
    statement_id = Column(Integer, ForeignKey("statements.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    statement = relationship("Statement", back_populates="transactions")

class Statement(Base):
    __tablename__ = "statements"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    account_type = Column(String, nullable=False)
    currency = Column(String, default="USD", nullable=False)  # Default currency for statement
    upload_date = Column(DateTime, default=datetime.utcnow)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    
    transactions = relationship("Transaction", back_populates="statement", cascade="all, delete-orphan")

class Analysis(Base):
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    total_spending = Column(Float, nullable=False)
    total_income = Column(Float, default=0.0, nullable=False)
    category_breakdown = Column(Text, nullable=True)  # JSON string
    savings_recommendations = Column(Text, nullable=True)  # JSON string
    psychological_profile = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)

class CategoryLearning(Base):
    __tablename__ = "category_learning"
    
    id = Column(Integer, primary_key=True, index=True)
    vendor_pattern = Column(String, nullable=False)  # Vendor/merchant name pattern
    description_pattern = Column(String, nullable=True)  # Description pattern
    category = Column(String, nullable=False)
    subcategory = Column(String, nullable=True)
    transaction_type = Column(String, default="debit", nullable=False)  # debit or credit
    confidence = Column(Float, default=1.0, nullable=False)  # Learning confidence score
    usage_count = Column(Integer, default=1, nullable=False)  # How many times this rule was used
    created_at = Column(DateTime, default=datetime.utcnow)
