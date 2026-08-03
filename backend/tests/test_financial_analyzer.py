from datetime import datetime

from analytics.financial_analyzer import FinancialAnalyzer


def test_analysis_separates_income_and_expenses_and_uses_currency_code():
    transactions = [
        {
            "date": datetime(2024, 1, 1),
            "amount": 50.0,
            "category": "Food & Dining",
            "transaction_type": "debit",
            "description": "Cafe",
        },
        {
            "date": datetime(2024, 1, 2),
            "amount": 100.0,
            "category": "Income",
            "transaction_type": "credit",
            "description": "Salary",
        },
    ]
    result = FinancialAnalyzer().analyze_month(transactions, 1, 2024, "INR")
    assert result["total_spending"] == 50.0
    assert result["total_income"] == 100.0
    assert all("$" not in item["message"] for item in result["savings_recommendations"])


def test_zero_value_transactions_do_not_divide_by_zero():
    profile = FinancialAnalyzer()._analyze_impulse_spending(
        [{"amount": 0.0, "description": "Shop"}]
    )
    assert profile["risk_level"] == "low"


def test_refunds_and_card_payments_do_not_inflate_income():
    transactions = [
        {
            "date": datetime(2024, 1, 1),
            "amount": 100.0,
            "category": "Shopping",
            "transaction_type": "debit",
            "account_type": "credit_card",
            "description": "Store purchase",
        },
        {
            "date": datetime(2024, 1, 2),
            "amount": 20.0,
            "category": "Refunds",
            "transaction_type": "refund",
            "account_type": "credit_card",
            "description": "Merchant refund",
        },
        {
            "date": datetime(2024, 1, 3),
            "amount": 80.0,
            "category": "Transfers",
            "transaction_type": "credit",
            "account_type": "credit_card",
            "description": "Payment thank you",
        },
    ]
    result = FinancialAnalyzer().analyze_month(transactions, 1, 2024)
    assert result["gross_spending"] == 100.0
    assert result["total_refunds"] == 20.0
    assert result["net_spending"] == 80.0
    assert result["total_income"] == 0
    assert result["excluded_transfers"] == 80.0


def test_recommendations_require_recorded_income():
    transaction = {
        "date": datetime(2024, 1, 1),
        "amount": 100.0,
        "category": "Shopping",
        "transaction_type": "debit",
        "description": "Store purchase",
    }
    result = FinancialAnalyzer().analyze_month([transaction], 1, 2024)
    assert result["savings_recommendations"] == []
