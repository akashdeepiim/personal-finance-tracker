'use client'

import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import { motion } from 'framer-motion'
import { getAnalysis, getAnalysisPeriods, getCategories } from '@/lib/api'
import { format } from 'date-fns'
import { AlertCircle, ArrowDownUp, ReceiptText, WalletCards } from 'lucide-react'
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts'
import { formatCurrency } from '@/lib/currency'
import type { Analysis, AnalysisPeriod, CategoriesResponse, CategoryItem, Recommendation } from '@/lib/types'

const COLORS = ['#2563eb', '#7c3aed', '#db2777', '#d97706', '#059669', '#dc2626', '#0891b2', '#65a30d']

export default function Dashboard({ currency = 'USD' }: { currency?: string }) {
  const now = new Date()
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [categories, setCategories] = useState<CategoriesResponse | null>(null)
  const [periods, setPeriods] = useState<AnalysisPeriod[]>([])
  const [selectedMonth, setSelectedMonth] = useState(now.getMonth() + 1)
  const [selectedYear, setSelectedYear] = useState(now.getFullYear())
  const [periodsReady, setPeriodsReady] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    getAnalysisPeriods()
      .then((result) => {
        if (!active) return
        const available = result.periods as AnalysisPeriod[]
        setPeriods(available)
        if (available.length) {
          setSelectedYear(available[0].year)
          setSelectedMonth(available[0].month)
        }
      })
      .catch(() => active && setError('Could not load available statement periods.'))
      .finally(() => active && setPeriodsReady(true))
    return () => { active = false }
  }, [])

  const loadData = useCallback(async () => {
    if (!periodsReady) return
    if (periods.length === 0) {
      setAnalysis(null)
      setCategories(null)
      setError('')
      setLoading(false)
      return
    }
    setLoading(true)
    setError('')
    const [analysisResult, categoriesResult] = await Promise.allSettled([
      getAnalysis(selectedYear, selectedMonth, currency),
      getCategories(currency, selectedMonth, selectedYear),
    ])
    setAnalysis(analysisResult.status === 'fulfilled' ? analysisResult.value : null)
    setCategories(categoriesResult.status === 'fulfilled' ? categoriesResult.value : null)
    if (analysisResult.status === 'rejected') {
      const detail = axios.isAxiosError(analysisResult.reason)
        ? analysisResult.reason.response?.data?.detail
        : undefined
      setError(detail || 'Analysis could not be loaded. Please try again.')
    }
    setLoading(false)
  }, [currency, periods.length, periodsReady, selectedMonth, selectedYear])

  useEffect(() => { void loadData() }, [loadData])

  if (loading || !periodsReady) {
    return <div className="flex h-64 items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" /></div>
  }

  const categoryData = categories?.categories?.map((category: CategoryItem) => ({
    name: category.name, value: category.amount, percentage: category.percentage,
  })) || []
  const recommendations = analysis?.savings_recommendations || []
  const changePeriod = (value: string) => {
    const [year, month] = value.split('-').map(Number)
    setSelectedYear(year)
    setSelectedMonth(month)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 rounded-lg bg-white p-4 shadow sm:flex-row sm:items-center">
        <label htmlFor="analysis-period" className="text-sm font-medium text-gray-700">Statement period</label>
        <select id="analysis-period" value={`${selectedYear}-${selectedMonth}`} onChange={(event) => changePeriod(event.target.value)} disabled={!periods.length} className="rounded border px-3 py-2">
          {periods.length ? periods.map((period) => (
            <option key={`${period.year}-${period.month}`} value={`${period.year}-${period.month}`}>
              {format(new Date(period.year, period.month - 1, 1), 'MMMM yyyy')} · {period.transaction_count} transaction{period.transaction_count === 1 ? '' : 's'}
            </option>
          )) : <option>No imported periods</option>}
        </select>
      </div>

      {error && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">{error}</div>}
      {!analysis && !error && <p className="rounded-lg bg-blue-50 p-4 text-center text-gray-700">Upload a statement to generate analysis.</p>}

      {analysis && <>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <SummaryCard label="Net spending" value={formatCurrency(analysis.net_spending, currency)} detail={`${formatCurrency(analysis.gross_spending, currency)} gross`} icon={<ReceiptText />} color="blue" />
          <SummaryCard label="Recorded income" value={formatCurrency(analysis.total_income, currency)} detail={`${analysis.transaction_count} transactions`} icon={<WalletCards />} color="green" />
          <SummaryCard label="Net cash flow" value={formatCurrency(analysis.net_cash_flow, currency)} detail={analysis.net_cash_flow >= 0 ? 'Income and refunds minus expenses' : 'Negative for this period'} icon={<ArrowDownUp />} color={analysis.net_cash_flow >= 0 ? 'purple' : 'pink'} />
          <SummaryCard label="Refunds" value={formatCurrency(analysis.total_refunds, currency)} detail={`${formatCurrency(analysis.excluded_transfers, currency)} transfers excluded`} icon={<AlertCircle />} color="slate" />
        </div>

        {categoryData.length > 0 && <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <ChartCard title="Expense share by category">
            <ResponsiveContainer width="100%" height={300}><PieChart><Pie data={categoryData} dataKey="value" nameKey="name" outerRadius={100} label={({ payload }) => payload.percentage >= 5 ? `${payload.name}: ${payload.percentage.toFixed(0)}%` : ''}>{categoryData.map((entry, index) => <Cell key={`${entry.name}-${index}`} fill={COLORS[index % COLORS.length]} />)}</Pie><Tooltip formatter={(value) => formatCurrency(Number(value ?? 0), currency)} /></PieChart></ResponsiveContainer>
          </ChartCard>
          <ChartCard title="Expenses by category">
            <ResponsiveContainer width="100%" height={300}><BarChart data={categoryData} margin={{ bottom: 60 }}><XAxis dataKey="name" angle={-35} textAnchor="end" interval={0} /><YAxis /><Tooltip formatter={(value) => formatCurrency(Number(value ?? 0), currency)} /><Bar dataKey="value" name="Expenses" fill="#2563eb" /></BarChart></ResponsiveContainer>
          </ChartCard>
        </div>}

        <section className="rounded-xl bg-white p-6 shadow-lg">
          <h2 className="mb-1 flex items-center text-xl font-bold text-gray-800"><AlertCircle className="mr-2 text-orange-500" />Budget rule checks</h2>
          <p className="mb-4 text-sm text-gray-600">These checks compare recorded expenses with recorded income using app defaults. They are starting points, not personalized financial advice.</p>
          {analysis.total_income <= 0 && <p className="rounded bg-amber-50 p-3 text-sm text-amber-900">No income was identified in this period, so income-based checks are unavailable. Mark income, refunds, and transfers correctly in Timeline.</p>}
          {analysis.total_income > 0 && recommendations.length === 0 && <p className="text-sm text-gray-600">No category exceeded the app’s current rule-of-thumb settings.</p>}
          <div className="space-y-3">{recommendations.map((rec: Recommendation) => (
            <div key={rec.category} className={`rounded-lg border-l-4 p-4 ${rec.severity === 'high' ? 'border-red-500 bg-red-50' : 'border-amber-500 bg-amber-50'}`}>
              <div className="flex flex-col justify-between gap-2 sm:flex-row"><div><h3 className="font-semibold text-gray-800">{rec.category}</h3><p className="mt-1 text-sm text-gray-700">{rec.message}</p><p className="mt-2 text-xs text-gray-600">Recorded: {rec.current_percentage}% · App setting: {rec.recommended_percentage}%</p></div><p className="font-bold text-green-700">{formatCurrency(rec.potential_savings, currency)}</p></div>
            </div>
          ))}</div>
        </section>
        <p className="text-xs text-gray-500">{analysis.analysis_note}</p>
      </>}
    </div>
  )
}

function SummaryCard({ label, value, detail, icon, color }: { label: string; value: string; detail: string; icon: React.ReactNode; color: string }) {
  const colors: Record<string, string> = { blue: 'from-blue-500 to-blue-600', green: 'from-emerald-500 to-emerald-600', purple: 'from-purple-500 to-purple-600', pink: 'from-pink-500 to-pink-600', slate: 'from-slate-600 to-slate-700' }
  return <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className={`rounded-xl bg-gradient-to-br ${colors[color]} p-5 text-white shadow-lg`}><div className="flex justify-between gap-3"><div><p className="text-sm text-white/80">{label}</p><p className="mt-2 text-2xl font-bold">{value}</p><p className="mt-1 text-xs text-white/75">{detail}</p></div><span className="opacity-80">{icon}</span></div></motion.div>
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="rounded-xl bg-white p-6 shadow-lg"><h2 className="mb-4 text-xl font-bold text-gray-800">{title}</h2>{children}</section>
}
