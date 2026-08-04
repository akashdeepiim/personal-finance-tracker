from collections import defaultdict
from typing import Dict, List


class FinancialAnalyzer:
    """Deterministic cash-flow analysis. It does not infer psychology."""

    # Optional category guardrails, expressed as a share of recorded income.
    # These are product defaults, not universal financial advice.
    category_thresholds = {
        "Food & Dining": 0.15,
        "Shopping": 0.10,
        "Transportation": 0.10,
        "Bills & Utilities": 0.20,
        "Entertainment": 0.05,
        "Groceries": 0.10,
        "Subscriptions": 0.03,
    }

    REFUND_WORDS = ("refund", "reversal", "cashback", "cash back", "chargeback")
    CARD_PAYMENT_WORDS = (
        "credit card payment",
        "card payment",
        "payment thank you",
        "autopay payment",
        "payment received",
    )

    def classify_transaction(self, transaction: Dict) -> str:
        """Return expense, income, refund, or transfer for analysis.

        Explicit user-selected types win. Legacy credit/debit records receive a
        conservative description/account-aware classification.
        """
        transaction_type = transaction.get("transaction_type", "debit")
        if transaction_type in {"refund", "transfer"}:
            return transaction_type

        description = (transaction.get("description") or "").lower()
        account_type = transaction.get("account_type")
        category = transaction.get("category") or "Other"

        if any(word in description for word in self.CARD_PAYMENT_WORDS):
            return "transfer"
        if transaction_type == "credit" and any(
            word in description for word in self.REFUND_WORDS
        ):
            return "refund"
        # An unlabelled credit on a credit-card account is generally a refund
        # or payment, not earnings. Users can explicitly mark genuine income.
        if transaction_type == "credit" and account_type == "credit_card":
            return "income" if category == "Income" else "refund"
        return "income" if transaction_type == "credit" else "expense"

    def analyze_month(
        self, transactions: List[Dict], month: int, year: int, currency: str = "USD"
    ) -> Dict:
        month_transactions = [
            t
            for t in transactions
            if t["date"].month == month and t["date"].year == year
        ]
        classified = defaultdict(list)
        for transaction in month_transactions:
            classified[self.classify_transaction(transaction)].append(transaction)

        expenses = classified["expense"]
        income = classified["income"]
        refunds = classified["refund"]
        transfers = classified["transfer"]
        gross_spending = sum(float(t["amount"]) for t in expenses)
        total_income = sum(float(t["amount"]) for t in income)
        total_refunds = sum(float(t["amount"]) for t in refunds)
        net_spending = max(gross_spending - total_refunds, 0.0)
        net_cash_flow = total_income + total_refunds - gross_spending
        category_breakdown = self._get_category_breakdown(expenses)

        return {
            "month": month,
            "year": year,
            "total_spending": gross_spending,
            "gross_spending": gross_spending,
            "total_refunds": total_refunds,
            "net_spending": net_spending,
            "total_income": total_income,
            "net_income": net_cash_flow,  # Backward-compatible name.
            "net_cash_flow": net_cash_flow,
            "excluded_transfers": sum(float(t["amount"]) for t in transfers),
            "category_breakdown": category_breakdown,
            "savings_recommendations": self._generate_savings_recommendations(
                category_breakdown, net_spending, total_income, currency
            ),
            "psychological_profile": self._generate_psychological_profile(
                expenses, category_breakdown
            ),
            "transaction_count": len(month_transactions),
            "expense_count": len(expenses),
            "income_count": len(income),
            "refund_count": len(refunds),
            "transfer_count": len(transfers),
            "analysis_note": (
                "Transfers are excluded. Refunds reduce net spending. Category "
                "checks are configurable rules of thumb, not financial advice."
            ),
        }

    def _get_category_breakdown(self, transactions: List[Dict]) -> Dict:
        breakdown = defaultdict(float)
        for transaction in transactions:
            category = transaction.get("category") or "Other"
            breakdown[category] += float(transaction["amount"])
        total = sum(breakdown.values())
        return {
            category: {
                "amount": amount,
                "percentage": amount / total * 100 if total else 0,
            }
            for category, amount in breakdown.items()
        }

    def _generate_savings_recommendations(
        self,
        category_breakdown: Dict,
        total_spending: float,
        total_income: float = 0,
        currency: str = "USD",
    ) -> List[Dict]:
        # Do not invent income from spending. Without recorded income, a
        # percentage-of-income comparison has no valid denominator.
        if total_income <= 0:
            return []

        recommendations = []
        if total_spending > total_income:
            recommendations.append(
                {
                    "category": "Overall cash flow",
                    "current_percentage": round(total_spending / total_income * 100, 2),
                    "recommended_percentage": 100.0,
                    "potential_savings": round(total_spending - total_income, 2),
                    "severity": "high",
                    "message": (
                        f"Recorded expenses exceed recorded income by {currency} "
                        f"{total_spending - total_income:.2f}. Verify transfers and "
                        "missing income before changing your budget."
                    ),
                }
            )

        for category, data in category_breakdown.items():
            threshold = self.category_thresholds.get(category)
            if threshold is None:
                continue
            current = data["amount"] / total_income * 100
            threshold_percentage = threshold * 100
            if current <= threshold_percentage:
                continue
            potential_savings = data["amount"] - threshold * total_income
            recommendations.append(
                {
                    "category": category,
                    "current_percentage": round(current, 2),
                    "recommended_percentage": round(threshold_percentage, 2),
                    "potential_savings": round(potential_savings, 2),
                    "severity": "high"
                    if current - threshold_percentage > 5
                    else "medium",
                    "message": (
                        f"{category} is {current:.1f}% of recorded income, above the "
                        f"app's {threshold_percentage:.0f}% rule-of-thumb setting. "
                        "Review this category if that target fits your situation."
                    ),
                }
            )
        return sorted(
            recommendations, key=lambda item: item["potential_savings"], reverse=True
        )

    def _generate_psychological_profile(
        self, transactions: List[Dict], category_breakdown: Dict
    ) -> Dict:
        """Return neutral, observable spending-pattern summaries."""
        return {
            "spending_personality": self._determine_spending_personality(transactions),
            # Keep the response key for compatibility; its content is now a
            # discretionary-spending indicator rather than an impulse claim.
            "impulse_indicators": self._analyze_impulse_spending(transactions),
            "financial_habits": self._analyze_habits(transactions),
            "risk_factors": self._identify_risk_factors(category_breakdown),
            "strengths": self._identify_strengths(category_breakdown),
        }

    def _determine_spending_personality(self, transactions: List[Dict]) -> str:
        if len(transactions) < 5:
            return "Insufficient data"
        average = sum(float(t["amount"]) for t in transactions) / len(transactions)
        large_count = sum(float(t["amount"]) > average * 2 for t in transactions)
        if large_count > len(transactions) * 0.3:
            return "Several above-average purchases"
        if len(transactions) > 50:
            return "High transaction frequency"
        return "No dominant spending pattern"

    def _analyze_impulse_spending(self, transactions: List[Dict]) -> Dict:
        discretionary_categories = {"Shopping", "Entertainment", "Food & Dining"}
        selected = [
            transaction
            for transaction in transactions
            if transaction.get("category") in discretionary_categories
        ]
        selected_total = sum(float(t["amount"]) for t in selected)
        total = sum(float(t["amount"]) for t in transactions)
        percentage = selected_total / total * 100 if total else 0
        return {
            "count": len(selected),
            "total": round(selected_total, 2),
            "percentage": round(percentage, 2),
            "risk_level": "high"
            if percentage > 50
            else "medium"
            if percentage > 30
            else "low",
        }

    def _analyze_habits(self, transactions: List[Dict]) -> List[str]:
        observations = []
        subscriptions = [
            t for t in transactions if t.get("category") == "Subscriptions"
        ]
        if subscriptions:
            observations.append(f"{len(subscriptions)} subscription charge(s) recorded")
        dining = [t for t in transactions if t.get("category") == "Food & Dining"]
        if dining:
            observations.append(
                f"{len(dining)} food and dining transaction(s) recorded"
            )
        return observations or ["No repeated category patterns detected"]

    def _identify_risk_factors(self, category_breakdown: Dict) -> List[str]:
        concentrations = [
            f"{category} represents {data['percentage']:.1f}% of recorded expenses"
            for category, data in category_breakdown.items()
            if data["percentage"] >= 40
        ]
        return concentrations or ["No category represents 40% or more of expenses"]

    def _identify_strengths(self, category_breakdown: Dict) -> List[str]:
        if not category_breakdown:
            return ["Not enough expense data for observations"]
        if len(category_breakdown) >= 4:
            return ["Expenses are distributed across at least four categories"]
        return ["Review more months before drawing conclusions"]
