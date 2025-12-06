from typing import List, Dict
from datetime import datetime
from collections import defaultdict
import json

class FinancialAnalyzer:
    """Analyze financial data and provide insights"""
    
    def __init__(self):
        self.category_thresholds = {
            'Food & Dining': 0.15,  # 15% of income
            'Shopping': 0.10,
            'Transportation': 0.10,
            'Bills & Utilities': 0.20,
            'Entertainment': 0.05,
            'Healthcare': 0.10,
            'Education': 0.05,
            'Travel': 0.05,
            'Groceries': 0.10,
            'Subscriptions': 0.03,
        }
    
    def analyze_month(self, transactions: List[Dict], month: int, year: int) -> Dict:
        """Analyze transactions for a specific month"""
        month_transactions = [
            t for t in transactions
            if t['date'].month == month and t['date'].year == year
        ]
        
        if not month_transactions:
            return {}
        
        # Separate income and expenses
        expenses = [t for t in month_transactions if t.get('transaction_type', 'debit') == 'debit']
        income = [t for t in month_transactions if t.get('transaction_type', 'debit') == 'credit']
        
        total_spending = sum(t['amount'] for t in expenses)
        total_income = sum(t['amount'] for t in income)
        net_income = total_income - total_spending
        
        category_breakdown = self._get_category_breakdown(expenses)  # Only analyze expenses
        savings_recommendations = self._generate_savings_recommendations(
            category_breakdown, total_spending, total_income
        )
        psychological_profile = self._generate_psychological_profile(
            month_transactions, category_breakdown
        )
        
        return {
            'month': month,
            'year': year,
            'total_spending': total_spending,
            'total_income': total_income,
            'net_income': net_income,
            'category_breakdown': category_breakdown,
            'savings_recommendations': savings_recommendations,
            'psychological_profile': psychological_profile,
            'transaction_count': len(month_transactions),
            'expense_count': len(expenses),
            'income_count': len(income)
        }
    
    def _get_category_breakdown(self, transactions: List[Dict]) -> Dict:
        """Calculate spending by category"""
        breakdown = defaultdict(float)
        for t in transactions:
            category = t.get('category', 'Other')
            breakdown[category] += t['amount']
        
        total = sum(breakdown.values())
        percentage_breakdown = {
            cat: {
                'amount': amount,
                'percentage': (amount / total * 100) if total > 0 else 0
            }
            for cat, amount in breakdown.items()
        }
        
        return percentage_breakdown
    
    def _generate_savings_recommendations(
        self, category_breakdown: Dict, total_spending: float, total_income: float = 0
    ) -> List[Dict]:
        """Generate savings recommendations"""
        recommendations = []
        
        # Use actual income if available, otherwise estimate
        estimated_income = total_income if total_income > 0 else (total_spending / 0.8 if total_spending > 0 else 0)
        
        # Add net income recommendation if spending exceeds income
        if total_income > 0 and total_spending > total_income:
            recommendations.append({
                'category': 'Overall Budget',
                'current_percentage': 100.0,
                'recommended_percentage': 80.0,
                'potential_savings': total_spending - total_income,
                'severity': 'high',
                'message': f'Your expenses (${total_spending:.2f}) exceed your income (${total_income:.2f}). Consider reducing spending by ${total_spending - total_income:.2f} to break even.'
            })
        
        for category, data in category_breakdown.items():
            percentage = data['percentage']
            threshold = self.category_thresholds.get(category, 0.10) * 100
            
            if percentage > threshold:
                excess = percentage - threshold
                potential_savings = (excess / 100) * total_spending
                
                recommendations.append({
                    'category': category,
                    'current_percentage': round(percentage, 2),
                    'recommended_percentage': round(threshold, 2),
                    'potential_savings': round(potential_savings, 2),
                    'severity': 'high' if excess > 5 else 'medium',
                    'message': self._get_recommendation_message(category, excess, potential_savings)
                })
        
        # Sort by potential savings
        recommendations.sort(key=lambda x: x['potential_savings'], reverse=True)
        
        return recommendations
    
    def _get_recommendation_message(self, category: str, excess: float, savings: float) -> str:
        """Generate recommendation message"""
        messages = {
            'Food & Dining': f"You're spending {excess:.1f}% more than recommended on dining out. Consider cooking more at home to save ${savings:.0f}/month.",
            'Shopping': f"Your shopping expenses are {excess:.1f}% above the recommended threshold. Review subscriptions and impulse purchases to save ${savings:.0f}/month.",
            'Transportation': f"Transportation costs are {excess:.1f}% high. Consider carpooling or public transit to save ${savings:.0f}/month.",
            'Entertainment': f"Entertainment spending is {excess:.1f}% above recommended. Look for free activities to save ${savings:.0f}/month.",
            'Subscriptions': f"You have {excess:.1f}% excess in subscriptions. Cancel unused services to save ${savings:.0f}/month.",
        }
        
        return messages.get(
            category,
            f"Consider reducing {category} spending by {excess:.1f}% to save ${savings:.0f}/month."
        )
    
    def _generate_psychological_profile(
        self, transactions: List[Dict], category_breakdown: Dict
    ) -> Dict:
        """Generate psychological financial profile"""
        profile = {
            'spending_personality': self._determine_spending_personality(transactions),
            'impulse_indicators': self._analyze_impulse_spending(transactions),
            'financial_habits': self._analyze_habits(transactions),
            'risk_factors': self._identify_risk_factors(category_breakdown),
            'strengths': self._identify_strengths(category_breakdown),
        }
        
        return profile
    
    def _determine_spending_personality(self, transactions: List[Dict]) -> str:
        """Determine spending personality type"""
        if len(transactions) < 5:
            return "Insufficient Data"
        
        # Analyze transaction frequency and amounts
        avg_amount = sum(t['amount'] for t in transactions) / len(transactions)
        large_transactions = [t for t in transactions if t['amount'] > avg_amount * 2]
        
        if len(large_transactions) > len(transactions) * 0.3:
            return "Big Spender"
        elif len(transactions) > 50:
            return "Frequent Spender"
        else:
            return "Balanced Spender"
    
    def _analyze_impulse_spending(self, transactions: List[Dict]) -> Dict:
        """Analyze impulse spending patterns"""
        impulse_keywords = ['amazon', 'target', 'walmart', 'store', 'shop']
        impulse_transactions = [
            t for t in transactions
            if any(kw in t.get('description', '').lower() for kw in impulse_keywords)
        ]
        
        impulse_total = sum(t['amount'] for t in impulse_transactions)
        total = sum(t['amount'] for t in transactions)
        
        return {
            'count': len(impulse_transactions),
            'total': round(impulse_total, 2),
            'percentage': round((impulse_total / total * 100) if total > 0 else 0, 2),
            'risk_level': 'high' if (impulse_total / total) > 0.3 else 'medium' if (impulse_total / total) > 0.15 else 'low'
        }
    
    def _analyze_habits(self, transactions: List[Dict]) -> List[str]:
        """Analyze financial habits"""
        habits = []
        
        # Check for subscription patterns
        subscriptions = [t for t in transactions if 'subscription' in t.get('description', '').lower()]
        if len(subscriptions) > 3:
            habits.append("Multiple active subscriptions")
        
        # Check for dining out frequency
        dining = [t for t in transactions if t.get('category') == 'Food & Dining']
        if len(dining) > 15:
            habits.append("Frequent dining out")
        
        # Check for consistent spending
        if len(transactions) > 0:
            amounts = [t['amount'] for t in transactions]
            if max(amounts) / (sum(amounts) / len(amounts)) < 3:
                habits.append("Consistent spending patterns")
        
        return habits if habits else ["No significant patterns detected"]
    
    def _identify_risk_factors(self, category_breakdown: Dict) -> List[str]:
        """Identify financial risk factors"""
        risks = []
        
        for category, data in category_breakdown.items():
            percentage = data['percentage']
            threshold = self.category_thresholds.get(category, 0.10) * 100
            
            if percentage > threshold * 1.5:
                risks.append(f"Excessive spending in {category} ({percentage:.1f}%)")
        
        return risks if risks else ["No major risk factors identified"]
    
    def _identify_strengths(self, category_breakdown: Dict) -> List[str]:
        """Identify financial strengths"""
        strengths = []
        
        essential_categories = ['Bills & Utilities', 'Groceries', 'Healthcare']
        for category in essential_categories:
            if category in category_breakdown:
                data = category_breakdown[category]
                threshold = self.category_thresholds.get(category, 0.10) * 100
                if data['percentage'] <= threshold:
                    strengths.append(f"Good control over {category} spending")
        
        return strengths if strengths else ["Building good financial habits"]

