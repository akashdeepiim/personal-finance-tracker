from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import extract
from datetime import datetime
from typing import List, Optional
import json

from database import get_db, engine, Base
from models import Transaction, Statement, Analysis, CategoryLearning
from parsers.statement_parser import StatementParser
from analytics.financial_analyzer import FinancialAnalyzer
from services.currency_converter import CurrencyConverter
from services.category_learner import CategoryLearner

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Personal Finance Tracker API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

parser = StatementParser()
analyzer = FinancialAnalyzer()
currency_converter = CurrencyConverter()
category_learner = CategoryLearner()

@app.get("/")
def read_root():
    return {"message": "Personal Finance Tracker API"}

@app.post("/api/upload-statement")
async def upload_statement(
    file: UploadFile = File(...),
    account_type: str = Form("credit_card"),
    db: Session = Depends(get_db)
):
    """Upload and parse a statement file"""
    try:
        content = await file.read()
        transactions_data = parser.parse_file(content, file.filename, account_type)
        
        if not transactions_data:
            raise HTTPException(status_code=400, detail="No transactions found in file")
        
        # Get month and year from first transaction
        first_date = transactions_data[0]['date']
        month = first_date.month
        year = first_date.year
        
        # Detect statement currency (use most common currency from transactions)
        currencies = [t.get('currency', 'USD') for t in transactions_data]
        statement_currency = max(set(currencies), key=currencies.count) if currencies else 'USD'
        
        # Create statement record
        statement = Statement(
            filename=file.filename,
            account_type=account_type,
            currency=statement_currency,
            month=month,
            year=year
        )
        db.add(statement)
        db.flush()
        
        # Create transaction records with currency conversion
        for t_data in transactions_data:
            try:
                original_amount = t_data.get('original_amount', t_data.get('amount', 0))
                currency = t_data.get('currency', 'USD')
                description = t_data.get('description', 'Unknown')
                
                # Ensure currency is valid
                if not currency or currency not in currency_converter.get_supported_currencies():
                    currency = 'USD'
                
                # Determine transaction type (credit = income, debit = expense)
                # For credit cards: 
                #   - Negative amounts = credits (payments/refunds = money coming in = income)
                #   - Positive amounts = debits (purchases = money going out = expenses)
                # For bank accounts:
                #   - Positive amounts = credits (deposits = money coming in = income)
                #   - Negative amounts = debits (withdrawals = money going out = expenses)
                if account_type == 'credit_card':
                    # Credit card: negative = payment/refund (income), positive = purchase (expense)
                    transaction_type = 'credit' if original_amount < 0 else 'debit'
                else:
                    # Bank account: positive = deposit (income), negative = withdrawal (expense)
                    transaction_type = 'credit' if original_amount > 0 else 'debit'
                
                # Get suggested category from learning system
                try:
                    suggestion = category_learner.suggest_category(db, description, original_amount, account_type)
                except Exception as learn_error:
                    print(f"Category learning error: {learn_error}")
                    suggestion = None
                
                # Use suggested category if available, otherwise use parsed category
                category = suggestion['category'] if suggestion else t_data.get('category')
                subcategory = suggestion.get('subcategory') if suggestion else None
                if suggestion and suggestion.get('transaction_type'):
                    transaction_type = suggestion['transaction_type']
                
                # Convert to USD for storage
                try:
                    amount_usd = currency_converter.convert(abs(original_amount), currency, 'USD')
                except Exception as conv_error:
                    # If conversion fails, assume it's already in USD
                    print(f"Currency conversion failed: {conv_error}, using original amount")
                    amount_usd = abs(original_amount)
                    currency = 'USD'
                
                transaction = Transaction(
                    date=t_data['date'],
                    amount=amount_usd,  # Always store as positive, use transaction_type to differentiate
                    original_amount=abs(original_amount),
                    currency=currency,
                    description=description,
                    category=category,
                    subcategory=subcategory,
                    transaction_type=transaction_type,
                    account_type=account_type,
                    statement_id=statement.id
                )
                db.add(transaction)
            except Exception as t_error:
                print(f"Error processing transaction: {t_error}")
                continue  # Skip this transaction and continue with others
        
        db.commit()
        
        return {
            "message": "Statement uploaded successfully",
            "transactions_count": len(transactions_data),
            "statement_id": statement.id
        }
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Upload error: {error_detail}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/categories")
def get_categories(currency: Optional[str] = None, db: Session = Depends(get_db)):
    """Get spending breakdown by category"""
    transactions = db.query(Transaction).all()
    
    target_currency = (currency or 'USD').upper()
    category_totals = {}
    
    for t in transactions:
        # Only count expenses (debit transactions) for spending categories
        transaction_type = getattr(t, 'transaction_type', 'debit')
        if transaction_type == 'credit':
            continue  # Skip income transactions for spending categories
        
        cat = t.category or "Other"
        if cat not in category_totals:
            category_totals[cat] = 0
        
        original_currency = getattr(t, 'currency', 'USD')
        original_amount = getattr(t, 'original_amount', t.amount)
        
        # Convert to target currency
        if target_currency != 'USD':
            amount_usd = currency_converter.convert(original_amount, original_currency, 'USD')
            converted_amount = currency_converter.convert(amount_usd, 'USD', target_currency)
        else:
            converted_amount = currency_converter.convert(original_amount, original_currency, 'USD')
        
        category_totals[cat] += converted_amount
    
    total = sum(category_totals.values())
    
    return {
        "categories": [
            {
                "name": cat,
                "amount": amount,
                "percentage": (amount / total * 100) if total > 0 else 0
            }
            for cat, amount in sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
        ],
        "total": total
    }

@app.get("/api/analysis/{year}/{month}")
def get_analysis(year: int, month: int, db: Session = Depends(get_db)):
    """Get or generate analysis for a specific month"""
    # Check if analysis exists
    existing = db.query(Analysis).filter(
        Analysis.month == month,
        Analysis.year == year
    ).first()
    
    if existing:
        return {
            "month": existing.month,
            "year": existing.year,
            "total_spending": existing.total_spending,
            "total_income": getattr(existing, 'total_income', 0.0),
            "category_breakdown": json.loads(existing.category_breakdown),
            "savings_recommendations": json.loads(existing.savings_recommendations),
            "psychological_profile": json.loads(existing.psychological_profile)
        }
    
    # Generate new analysis
    transactions = db.query(Transaction).filter(
        extract('month', Transaction.date) == month,
        extract('year', Transaction.date) == year
    ).all()
    
    if not transactions:
        raise HTTPException(status_code=404, detail="No transactions found for this month")
    
    transactions_data = [
        {
            "date": t.date,
            "amount": t.amount,
            "description": t.description,
            "category": t.category,
            "transaction_type": getattr(t, 'transaction_type', 'debit')
        }
        for t in transactions
    ]
    
    analysis = analyzer.analyze_month(transactions_data, month, year)
    
    # Save analysis
    analysis_record = Analysis(
        month=month,
        year=year,
        total_spending=analysis['total_spending'],
        total_income=analysis.get('total_income', 0.0),
        category_breakdown=json.dumps(analysis['category_breakdown']),
        savings_recommendations=json.dumps(analysis['savings_recommendations']),
        psychological_profile=json.dumps(analysis['psychological_profile'])
    )
    db.add(analysis_record)
    db.commit()
    
    return analysis

@app.get("/api/trends")
def get_trends(
    months: int = 6,
    db: Session = Depends(get_db)
):
    """Get spending trends over time"""
    transactions = db.query(Transaction).all()
    
    monthly_totals = {}
    for t in transactions:
        key = f"{t.date.year}-{t.date.month:02d}"
        if key not in monthly_totals:
            monthly_totals[key] = 0
        monthly_totals[key] += t.amount
    
    # Sort by date
    sorted_months = sorted(monthly_totals.items())[-months:]
    
    return {
        "trends": [
            {"month": month, "total": total}
            for month, total in sorted_months
        ]
    }

@app.get("/api/psychological-profile")
def get_psychological_profile(db: Session = Depends(get_db)):
    """Get overall psychological financial profile"""
    # Get last 3 months of transactions
    recent_transactions = db.query(Transaction).order_by(
        Transaction.date.desc()
    ).limit(100).all()
    
    if not recent_transactions:
        return {"message": "Insufficient data"}
    
    transactions_data = [
        {
            "date": t.date,
            "amount": t.amount,
            "description": t.description,
            "category": t.category
        }
        for t in recent_transactions
    ]
    
    category_breakdown = analyzer._get_category_breakdown(transactions_data)
    profile = analyzer._generate_psychological_profile(transactions_data, category_breakdown)
    
    return profile

@app.delete("/api/transactions/{transaction_id}")
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    """Delete a transaction"""
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    db.delete(transaction)
    db.commit()
    
    return {"message": "Transaction deleted"}

@app.delete("/api/statements/{statement_id}")
def delete_statement(statement_id: int, db: Session = Depends(get_db)):
    """Delete a statement and all its transactions"""
    statement = db.query(Statement).filter(Statement.id == statement_id).first()
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")
    
    # Delete associated transactions (cascade should handle this, but explicit is better)
    deleted_count = db.query(Transaction).filter(Transaction.statement_id == statement_id).delete()
    db.delete(statement)
    db.commit()
    
    return {
        "message": "Statement and all associated transactions deleted",
        "deleted_transactions": deleted_count
    }

@app.delete("/api/data/clear-all")
def clear_all_data(db: Session = Depends(get_db)):
    """Delete all data from the database"""
    try:
        # Delete all transactions
        deleted_transactions = db.query(Transaction).delete()
        
        # Delete all statements
        deleted_statements = db.query(Statement).delete()
        
        # Delete all analyses
        deleted_analyses = db.query(Analysis).delete()
        
        db.commit()
        
        return {
            "message": "All data cleared successfully",
            "deleted_transactions": deleted_transactions,
            "deleted_statements": deleted_statements,
            "deleted_analyses": deleted_analyses
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error clearing data: {str(e)}")

@app.get("/api/statements")
def get_statements(db: Session = Depends(get_db)):
    """Get all uploaded statements"""
    statements = db.query(Statement).order_by(Statement.upload_date.desc()).all()
    
    return [
        {
            "id": s.id,
            "filename": s.filename,
            "account_type": s.account_type,
            "currency": getattr(s, 'currency', 'USD'),
            "upload_date": s.upload_date.isoformat(),
            "month": s.month,
            "year": s.year,
            "transaction_count": len(s.transactions)
        }
        for s in statements
    ]

@app.get("/api/currency/rates")
def get_currency_rates():
    """Get current exchange rates"""
    rates = currency_converter.get_rates()
    return {
        "base": "USD",
        "rates": rates,
        "supported_currencies": currency_converter.get_supported_currencies()
    }

@app.get("/api/currency/convert")
def convert_currency(
    amount: float,
    from_currency: str = "USD",
    to_currency: str = "USD"
):
    """Convert amount from one currency to another"""
    converted = currency_converter.convert(amount, from_currency, to_currency)
    return {
        "original_amount": amount,
        "from_currency": from_currency.upper(),
        "to_currency": to_currency.upper(),
        "converted_amount": converted,
        "rate": converted / amount if amount != 0 else 0
    }

@app.get("/api/transactions")
def get_transactions(
    month: Optional[int] = None,
    year: Optional[int] = None,
    category: Optional[str] = None,
    currency: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get transactions with optional filters and currency conversion"""
    query = db.query(Transaction)
    
    if month:
        query = query.filter(extract('month', Transaction.date) == month)
    if year:
        query = query.filter(extract('year', Transaction.date) == year)
    if category:
        query = query.filter(Transaction.category == category)
    
    transactions = query.order_by(Transaction.date.desc()).all()
    
    # Convert to requested currency if specified
    target_currency = (currency or 'USD').upper()
    
    result = []
    for t in transactions:
        original_currency = getattr(t, 'currency', 'USD')
        original_amount = getattr(t, 'original_amount', t.amount)
        
        # Convert amount if currency is specified
        if target_currency != 'USD':
            # First convert original to USD, then to target
            amount_usd = currency_converter.convert(original_amount, original_currency, 'USD')
            converted_amount = currency_converter.convert(amount_usd, 'USD', target_currency)
        else:
            converted_amount = currency_converter.convert(original_amount, original_currency, 'USD')
        
        result.append({
            "id": t.id,
            "date": t.date.isoformat(),
            "amount": converted_amount,
            "original_amount": original_amount,
            "currency": target_currency,
            "original_currency": original_currency,
            "description": t.description,
            "category": t.category,
            "subcategory": getattr(t, 'subcategory', None),
            "transaction_type": getattr(t, 'transaction_type', 'debit'),
            "account_type": t.account_type
        })
    
    return result

@app.put("/api/transactions/{transaction_id}")
def update_transaction(
    transaction_id: int,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    transaction_type: Optional[str] = None,
    apply_to_all_matching: bool = True,  # Automatically update matching vendors
    db: Session = Depends(get_db)
):
    """
    Update a transaction's category and learn from it.
    
    If apply_to_all_matching is True (default), also updates all other
    transactions from the same vendor with the new category.
    """
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Update transaction
    if category is not None:
        transaction.category = category
    if subcategory is not None:
        transaction.subcategory = subcategory
    if transaction_type is not None:
        transaction.transaction_type = transaction_type
    
    # Learn from this update
    try:
        category_learner.learn_from_transaction(db, transaction)
    except Exception as learn_error:
        print(f"Learning error (non-fatal): {learn_error}")
    
    # Update all matching vendor transactions if requested
    matching_updated = 0
    if apply_to_all_matching and category is not None:
        try:
            matching_updated = category_learner.update_matching_transactions(
                db, transaction, category, subcategory, transaction_type
            )
        except Exception as bulk_error:
            print(f"Bulk update error (non-fatal): {bulk_error}")
    
    db.commit()
    db.refresh(transaction)
    
    return {
        "message": "Transaction updated successfully",
        "transaction": {
            "id": transaction.id,
            "category": transaction.category,
            "subcategory": transaction.subcategory,
            "transaction_type": transaction.transaction_type
        },
        "matching_updated": matching_updated
    }

@app.get("/api/category-learning")
def get_category_learning(db: Session = Depends(get_db)):
    """Get all learned category patterns"""
    rules = category_learner.get_learning_rules(db)
    return {"rules": rules}

