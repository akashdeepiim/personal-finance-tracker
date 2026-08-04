from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Depends,
    HTTPException,
    Form,
    Header,
    Query,
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import extract, func
from sqlalchemy.exc import IntegrityError
from typing import Optional, Literal
import os
import secrets
import hashlib
from datetime import timezone
from pathlib import Path
from collections import defaultdict
from pydantic import BaseModel

from database import get_db
from models import Transaction, Statement, Analysis, CategoryLearning, User
from parsers.statement_parser import StatementParser
from analytics.financial_analyzer import FinancialAnalyzer
from services.currency_converter import CurrencyConverter
from services.category_learner import CategoryLearner
from migrate_db import migrate_database
from services.auth_service import (
    claim_legacy_data,
    create_session,
    clear_login_failures,
    DUMMY_PASSWORD_HASH,
    hash_password,
    normalize_email,
    login_allowed,
    record_login_failure,
    revoke_session,
    user_for_session,
    validate_password,
    verify_password,
)

ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
API_TOKEN = os.getenv("FINANCE_API_TOKEN")
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
if ENVIRONMENT == "production" and not API_TOKEN:
    raise RuntimeError("FINANCE_API_TOKEN is required when ENVIRONMENT=production")


def require_api_token(authorization: Optional[str] = Header(default=None)):
    if API_TOKEN:
        expected = f"Bearer {API_TOKEN}"
        if not authorization or not secrets.compare_digest(authorization, expected):
            raise HTTPException(status_code=401, detail="Invalid or missing API token")


# Create database tables
migrate_database()

app = FastAPI(title="Personal Finance Tracker API")


# CORS middleware
origins_str = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:8000,https://expenses.akash-deep.com",
)
origins = [origin.strip() for origin in origins_str.split(",")]

# For debugging - if origins contains "*", allow all origins
allow_all = "*" in origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all else origins,
    allow_credentials=not allow_all,  # credentials can't be used with "*"
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[],
)


parser = StatementParser()
analyzer = FinancialAnalyzer()
currency_converter = CurrencyConverter()
category_learner = CategoryLearner()


def validated_currency(value: Optional[str]) -> str:
    currency = (value or "USD").upper()
    if currency not in currency_converter.get_supported_currencies():
        raise HTTPException(status_code=400, detail=f"Unsupported currency: {currency}")
    return currency


class AuthRequest(BaseModel):
    email: str
    password: str


def current_user(
    x_session_token: Optional[str] = Header(default=None),
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    require_api_token(authorization)
    user = user_for_session(db, x_session_token)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


@app.get("/")
def read_root():
    return {"message": "Personal Finance Tracker API"}


@app.post("/api/auth/signup", status_code=201)
def signup(
    credentials: AuthRequest,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    require_api_token(authorization)
    try:
        email = normalize_email(credentials.email)
        validate_password(credentials.password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(
            status_code=409, detail="An account with this email already exists"
        )
    is_first_user = db.query(User.id).first() is None
    user = User(email=email, password_hash=hash_password(credentials.password))
    db.add(user)
    db.flush()
    if is_first_user:
        claim_legacy_data(db, user.id)
    token = create_session(db, user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="An account with this email already exists"
        ) from exc
    return {"token": token, "user": {"id": user.id, "email": user.email}}


@app.post("/api/auth/login")
def login(
    credentials: AuthRequest,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    require_api_token(authorization)
    try:
        email = normalize_email(credentials.email)
    except ValueError:
        email = ""
    if not login_allowed(db, email):
        raise HTTPException(
            status_code=429, detail="Too many sign-in attempts. Try again later."
        )
    user = db.query(User).filter(User.email == email).first()
    password_matches = verify_password(
        credentials.password, user.password_hash if user else DUMMY_PASSWORD_HASH
    )
    if not user or not password_matches:
        record_login_failure(db, email)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    clear_login_failures(db, email)
    token = create_session(db, user)
    db.commit()
    return {"token": token, "user": {"id": user.id, "email": user.email}}


@app.post("/api/auth/logout")
def logout(
    x_session_token: Optional[str] = Header(default=None),
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    require_api_token(authorization)
    revoke_session(db, x_session_token)
    return {"ok": True}


@app.get("/api/auth/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "email": user.email}


@app.post("/api/upload-statement")
async def upload_statement(
    file: UploadFile = File(...),
    account_type: Literal["credit_card", "bank_account"] = Form("credit_card"),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Upload and parse a statement file"""
    filename = Path(file.filename or "").name[:255]
    if Path(filename).suffix.lower() not in {".csv", ".pdf"}:
        raise HTTPException(
            status_code=400, detail="Only CSV and PDF statements are supported"
        )
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit",
        )
    raw_file_hash = hashlib.sha256(content).hexdigest()
    file_hash = hashlib.sha256(f"{user.id}:{raw_file_hash}".encode()).hexdigest()
    if (
        db.query(Statement)
        .filter(
            Statement.account_type == account_type,
            Statement.file_hash == file_hash,
            Statement.user_id == user.id,
        )
        .first()
    ):
        raise HTTPException(
            status_code=409, detail="This statement has already been uploaded"
        )
    try:
        transactions_data = parser.parse_file(content, filename, account_type)

        if not transactions_data:
            raise HTTPException(status_code=400, detail="No transactions found in file")

        # Get month and year from first transaction
        first_date = transactions_data[0]["date"]
        month = first_date.month
        year = first_date.year

        # Detect statement currency (use most common currency from transactions)
        currencies = [t.get("currency", "USD") for t in transactions_data]
        statement_currency = (
            max(set(currencies), key=currencies.count) if currencies else "USD"
        )

        # Create statement record
        statement = Statement(
            user_id=user.id,
            filename=filename,
            account_type=account_type,
            currency=statement_currency,
            file_hash=file_hash,
            month=month,
            year=year,
        )
        db.add(statement)
        db.flush()

        # Create transaction records with currency conversion
        saved_count = 0
        supported_currencies = set(currency_converter.get_supported_currencies())
        for t_data in transactions_data:
            original_amount = t_data.get("original_amount", t_data.get("amount", 0))
            currency = t_data.get("currency", "USD")
            description = str(t_data.get("description", "Unknown")).strip()[:500]

            # Ensure currency is valid
            if not currency or currency not in supported_currencies:
                raise ValueError(f"Unsupported currency: {currency}")

            # Preserve explicit neutral/refund classifications from the parser.
            parsed_type = t_data.get("transaction_type")
            if parsed_type in {"credit", "debit", "refund", "transfer"}:
                transaction_type = parsed_type
            elif account_type == "credit_card":
                # Credit card: negative = payment/refund (income), positive = purchase (expense)
                transaction_type = "credit" if original_amount < 0 else "debit"
            else:
                # Bank account: positive = deposit (income), negative = withdrawal (expense)
                transaction_type = "credit" if original_amount > 0 else "debit"

            suggestion = category_learner.suggest_category(
                db, user.id, description, original_amount, account_type
            )

            # Use suggested category if available, otherwise use parsed category
            category = suggestion["category"] if suggestion else t_data.get("category")
            subcategory = suggestion.get("subcategory") if suggestion else None
            if suggestion and suggestion.get("transaction_type"):
                transaction_type = suggestion["transaction_type"]

            # Convert to USD for normalized storage
            amount_usd = currency_converter.convert(
                abs(original_amount), currency, "USD"
            )

            transaction = Transaction(
                user_id=user.id,
                date=t_data["date"],
                amount=amount_usd,  # Always store as positive, use transaction_type to differentiate
                original_amount=abs(original_amount),
                currency=currency,
                description=description,
                category=category,
                subcategory=subcategory,
                transaction_type=transaction_type,
                account_type=account_type,
                statement_id=statement.id,
            )
            db.add(transaction)
            saved_count += 1

        db.commit()

        return {
            "message": "Statement uploaded successfully",
            "transactions_count": saved_count,
            "statement_id": statement.id,
        }
    except HTTPException:
        db.rollback()
        raise
    except (ValueError, KeyError, TypeError) as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail="Unable to process statement"
        ) from e


@app.get("/api/categories")
def get_categories(
    currency: Optional[str] = None,
    month: Optional[int] = Query(default=None, ge=1, le=12),
    year: Optional[int] = Query(default=None, ge=1900, le=2200),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Get spending breakdown by category"""
    query = db.query(Transaction).filter(Transaction.user_id == user.id)
    if month is not None:
        query = query.filter(extract("month", Transaction.date) == month)
    if year is not None:
        query = query.filter(extract("year", Transaction.date) == year)
    target_currency = validated_currency(currency)
    rows = (
        query.with_entities(
            func.coalesce(Transaction.category, "Other"), func.sum(Transaction.amount)
        )
        .filter(Transaction.transaction_type == "debit")
        .group_by(Transaction.category)
        .all()
    )
    category_totals = {
        category: float(currency_converter.convert(amount, "USD", target_currency))
        for category, amount in rows
    }

    total = sum(category_totals.values())

    return {
        "categories": [
            {
                "name": cat,
                "amount": amount,
                "percentage": (amount / total * 100) if total > 0 else 0,
            }
            for cat, amount in sorted(
                category_totals.items(), key=lambda x: x[1], reverse=True
            )
        ],
        "total": total,
    }


@app.get("/api/analysis/{year}/{month}")
def get_analysis(
    year: int,
    month: int,
    currency: str = "USD",
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Get or generate analysis for a specific month"""
    if not 1 <= month <= 12 or not 1900 <= year <= 2200:
        raise HTTPException(status_code=422, detail="Invalid month or year")
    target_currency = validated_currency(currency)

    # Generate new analysis
    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user.id,
            extract("month", Transaction.date) == month,
            extract("year", Transaction.date) == year,
        )
        .all()
    )

    if not transactions:
        raise HTTPException(
            status_code=404, detail="No transactions found for this month"
        )

    transactions_data = [
        {
            "date": t.date,
            "amount": float(
                currency_converter.convert(t.amount, "USD", target_currency)
            ),
            "description": t.description,
            "category": t.category,
            "transaction_type": getattr(t, "transaction_type", "debit"),
            "account_type": t.account_type,
        }
        for t in transactions
    ]

    analysis = analyzer.analyze_month(transactions_data, month, year, target_currency)

    return analysis


@app.get("/api/analysis-periods")
def get_analysis_periods(
    db: Session = Depends(get_db), user: User = Depends(current_user)
):
    """Return months that actually contain transactions, newest first."""
    rows = (
        db.query(
            extract("year", Transaction.date),
            extract("month", Transaction.date),
            func.count(Transaction.id),
        )
        .filter(Transaction.user_id == user.id)
        .group_by(extract("year", Transaction.date), extract("month", Transaction.date))
        .order_by(
            extract("year", Transaction.date).desc(),
            extract("month", Transaction.date).desc(),
        )
        .all()
    )
    return {
        "periods": [
            {"year": int(year), "month": int(month), "transaction_count": count}
            for year, month, count in rows
        ]
    }


@app.get("/api/trends")
def get_trends(
    months: int = Query(default=6, ge=1, le=60),
    currency: str = "USD",
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Get spending trends over time"""
    target_currency = validated_currency(currency)
    transactions = (
        db.query(Transaction)
        .filter(Transaction.user_id == user.id)
        .order_by(Transaction.date)
        .all()
    )
    monthly = defaultdict(list)
    for transaction in transactions:
        monthly[transaction.date.strftime("%Y-%m")].append(
            {
                "date": transaction.date,
                "amount": float(
                    currency_converter.convert(
                        transaction.amount, "USD", target_currency
                    )
                ),
                "description": transaction.description,
                "category": transaction.category,
                "transaction_type": transaction.transaction_type,
                "account_type": transaction.account_type,
            }
        )
    trend_rows = []
    for period in sorted(monthly)[-months:]:
        year, month = map(int, period.split("-"))
        result = analyzer.analyze_month(monthly[period], month, year, target_currency)
        trend_rows.append(
            {
                "month": period,
                "total": result["gross_spending"],
                "income": result["total_income"],
                "refunds": result["total_refunds"],
                "net_cash_flow": result["net_cash_flow"],
            }
        )
    return {"trends": trend_rows}


@app.get("/api/psychological-profile")
def get_psychological_profile(
    currency: str = "USD",
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Get overall psychological financial profile"""
    target_currency = validated_currency(currency)
    latest = (
        db.query(Transaction.date)
        .filter(Transaction.user_id == user.id)
        .order_by(Transaction.date.desc())
        .first()
    )
    if not latest:
        return {"message": "Insufficient data"}
    from dateutil.relativedelta import relativedelta

    cutoff = latest[0] - relativedelta(months=3)
    recent_transactions = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user.id,
            Transaction.date >= cutoff,
            Transaction.transaction_type == "debit",
        )
        .order_by(Transaction.date.desc())
        .all()
    )

    transactions_data = [
        {
            "date": t.date,
            "amount": float(
                currency_converter.convert(t.amount, "USD", target_currency)
            ),
            "description": t.description,
            "category": t.category,
        }
        for t in recent_transactions
    ]

    category_breakdown = analyzer._get_category_breakdown(transactions_data)
    profile = analyzer._generate_psychological_profile(
        transactions_data, category_breakdown
    )

    return profile


@app.delete("/api/transactions/{transaction_id}")
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Delete a transaction"""
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.user_id == user.id)
        .first()
    )
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(transaction)
    db.query(Analysis).filter(
        Analysis.user_id == user.id,
        Analysis.month == transaction.date.month,
        Analysis.year == transaction.date.year,
    ).delete()
    db.commit()

    return {"message": "Transaction deleted"}


@app.delete("/api/statements/{statement_id}")
def delete_statement(
    statement_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Delete a statement and all its transactions"""
    statement = (
        db.query(Statement)
        .filter(Statement.id == statement_id, Statement.user_id == user.id)
        .first()
    )
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")

    # Delete associated transactions (cascade should handle this, but explicit is better)
    deleted_count = (
        db.query(Transaction)
        .filter(
            Transaction.statement_id == statement_id,
            Transaction.user_id == user.id,
        )
        .delete()
    )
    db.query(Analysis).filter(
        Analysis.user_id == user.id,
        Analysis.month == statement.month,
        Analysis.year == statement.year,
    ).delete()
    db.delete(statement)
    db.commit()

    return {
        "message": "Statement and all associated transactions deleted",
        "deleted_transactions": deleted_count,
    }


@app.delete("/api/data/clear-all")
def clear_all_data(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Delete all data from the database"""
    try:
        # Delete all transactions
        deleted_transactions = (
            db.query(Transaction).filter(Transaction.user_id == user.id).delete()
        )

        # Delete all statements
        deleted_statements = (
            db.query(Statement).filter(Statement.user_id == user.id).delete()
        )

        # Delete all analyses
        deleted_analyses = (
            db.query(Analysis).filter(Analysis.user_id == user.id).delete()
        )
        deleted_learning_rules = (
            db.query(CategoryLearning)
            .filter(CategoryLearning.user_id == user.id)
            .delete()
        )

        db.commit()

        return {
            "message": "All data cleared successfully",
            "deleted_transactions": deleted_transactions,
            "deleted_statements": deleted_statements,
            "deleted_analyses": deleted_analyses,
            "deleted_learning_rules": deleted_learning_rules,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to clear data") from e


@app.get("/api/statements")
def get_statements(
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Get all uploaded statements"""
    statements = (
        db.query(Statement, func.count(Transaction.id))
        .outerjoin(Transaction, Transaction.statement_id == Statement.id)
        .filter(Statement.user_id == user.id)
        .group_by(Statement.id)
        .order_by(Statement.upload_date.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        {
            "id": s.id,
            "filename": s.filename,
            "account_type": s.account_type,
            "currency": getattr(s, "currency", "USD"),
            "upload_date": (
                s.upload_date
                if s.upload_date.tzinfo
                else s.upload_date.replace(tzinfo=timezone.utc)
            ).isoformat(),
            "month": s.month,
            "year": s.year,
            "transaction_count": transaction_count,
        }
        for s, transaction_count in statements
    ]


@app.get("/api/currency/rates")
def get_currency_rates(_user: User = Depends(current_user)):
    """Get current exchange rates"""
    rates = currency_converter.get_rates()
    return {
        "base": "USD",
        "rates": rates,
        "supported_currencies": currency_converter.get_supported_currencies(),
    }


@app.get("/api/currency/convert")
def convert_currency(
    amount: float,
    from_currency: str = "USD",
    to_currency: str = "USD",
    _user: User = Depends(current_user),
):
    """Convert amount from one currency to another"""
    try:
        converted = currency_converter.convert(amount, from_currency, to_currency)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "original_amount": amount,
        "from_currency": from_currency.upper(),
        "to_currency": to_currency.upper(),
        "converted_amount": float(converted),
        "rate": float(converted) / amount if amount != 0 else 0,
    }


@app.get("/api/transactions")
def get_transactions(
    month: Optional[int] = Query(default=None, ge=1, le=12),
    year: Optional[int] = Query(default=None, ge=1900, le=2200),
    category: Optional[str] = Query(default=None, max_length=100),
    currency: Optional[str] = None,
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Get transactions with optional filters and currency conversion"""
    query = db.query(Transaction).filter(Transaction.user_id == user.id)

    if month:
        query = query.filter(extract("month", Transaction.date) == month)
    if year:
        query = query.filter(extract("year", Transaction.date) == year)
    if category:
        query = query.filter(Transaction.category == category)

    transactions = (
        query.order_by(Transaction.date.desc()).offset(offset).limit(limit).all()
    )

    # Convert to requested currency if specified
    target_currency = validated_currency(currency)

    result = []
    for t in transactions:
        original_amount = getattr(t, "original_amount", t.amount)
        original_currency = getattr(t, "currency", "USD")
        converted_amount = currency_converter.convert(t.amount, "USD", target_currency)

        result.append(
            {
                "id": t.id,
                "date": t.date.isoformat(),
                "amount": float(converted_amount),
                "original_amount": float(original_amount),
                "currency": target_currency,
                "original_currency": original_currency,
                "description": t.description,
                "category": t.category,
                "subcategory": getattr(t, "subcategory", None),
                "transaction_type": getattr(t, "transaction_type", "debit"),
                "account_type": t.account_type,
            }
        )

    return result


@app.put("/api/transactions/{transaction_id}")
def update_transaction(
    transaction_id: int,
    category: Optional[str] = Query(default=None, max_length=100),
    subcategory: Optional[str] = Query(default=None, max_length=100),
    transaction_type: Optional[Literal["credit", "debit", "refund", "transfer"]] = None,
    apply_to_all_matching: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """
    Update a transaction's category and learn from it.

    If apply_to_all_matching is True, also updates all other
    transactions from the same vendor with the new category.
    """
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.user_id == user.id)
        .first()
    )
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Update transaction
    if category is not None:
        transaction.category = category
    if subcategory is not None:
        transaction.subcategory = subcategory
    if transaction_type is not None:
        transaction.transaction_type = transaction_type

    category_learner.learn_from_transaction(db, transaction)

    # Update all matching vendor transactions if requested
    matching_updated = 0
    if apply_to_all_matching and category is not None:
        matching_updated = category_learner.update_matching_transactions(
            db, transaction, category, subcategory, transaction_type
        )

    db.query(Analysis).filter(
        Analysis.user_id == user.id,
        Analysis.month == transaction.date.month,
        Analysis.year == transaction.date.year,
    ).delete()
    db.commit()
    db.refresh(transaction)

    return {
        "message": "Transaction updated successfully",
        "transaction": {
            "id": transaction.id,
            "category": transaction.category,
            "subcategory": transaction.subcategory,
            "transaction_type": transaction.transaction_type,
        },
        "matching_updated": matching_updated,
    }


@app.get("/api/category-learning")
def get_category_learning(
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Get all learned category patterns"""
    rules = category_learner.get_learning_rules(db, user.id, limit)
    return {"rules": rules}
