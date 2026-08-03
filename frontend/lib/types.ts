export interface CategoryItem { name: string; amount: number; percentage: number }
export interface CategoriesResponse { categories: CategoryItem[]; total: number }
export interface Transaction {
  id: number; date: string; amount: number; original_amount: number; currency: string;
  original_currency: string; description: string; category: string | null;
  subcategory: string | null; transaction_type: 'credit' | 'debit' | 'refund' | 'transfer'; account_type: string;
}
export interface Recommendation {
  category: string; current_percentage: number; recommended_percentage: number;
  potential_savings: number; severity: 'high' | 'medium'; message: string;
}
export interface Analysis {
  month: number; year: number; total_spending: number; total_income: number;
  gross_spending: number; total_refunds: number; net_spending: number;
  net_cash_flow: number; excluded_transfers: number; transaction_count: number;
  analysis_note: string;
  savings_recommendations: Recommendation[];
}
export interface AnalysisPeriod { year: number; month: number; transaction_count: number }
export interface PsychologicalProfileData {
  message?: string; spending_personality: string;
  impulse_indicators: { count: number; total: number; percentage: number; risk_level: 'high' | 'medium' | 'low' };
  financial_habits: string[]; risk_factors: string[]; strengths: string[];
}
export interface TrendsResponse { trends: Array<{ month: string; total: number; income: number; refunds: number; net_cash_flow: number }> }
export interface Statement { id: number; filename: string; account_type: string; currency: string; upload_date: string; transaction_count: number }
