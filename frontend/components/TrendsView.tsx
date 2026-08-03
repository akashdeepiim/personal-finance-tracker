'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { getTrends } from '@/lib/api'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts'
import { TrendingUp, TrendingDown } from 'lucide-react'
import { formatCurrency } from '@/lib/currency'
import type { TrendsResponse } from '@/lib/types'

interface TrendsViewProps {
  currency?: string
}

export default function TrendsView({ currency = 'USD' }: TrendsViewProps) {
  const [trends, setTrends] = useState<TrendsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [months, setMonths] = useState(6)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const trendsData = await getTrends(months, currency)
      setTrends(trendsData)
    } catch (error) {
      console.error('Error loading data:', error)
      setError('Trends could not be loaded. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [currency, months])

  useEffect(() => { void loadData() }, [loadData])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
          className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full"
        />
      </div>
    )
  }

  if (error) return <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">{error}</div>

  if (!trends || !trends.trends || trends.trends.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="text-center py-12"
      >
        <p className="text-gray-600 text-lg">No trend data available. Upload statements to see trends!</p>
      </motion.div>
    )
  }

  const trendData = trends.trends.map((t) => ({
    month: t.month,
    total: Math.round(t.total),
    income: Math.round(t.income),
    cashFlow: Math.round(t.net_cash_flow),
  }))

  // Calculate trend direction
  const firstMonth = trendData[0]?.total || 0
  const lastMonth = trendData[trendData.length - 1]?.total || 0
  const trendDirection = lastMonth > firstMonth ? 'up' : 'down'
  const trendPercentage = firstMonth > 0 ? Math.abs(((lastMonth - firstMonth) / firstMonth) * 100) : 0

  return (
    <div className="space-y-6">
      {/* Time Period Selector */}
      <div className="flex items-center space-x-4 bg-white p-4 rounded-lg shadow">
        <label className="text-sm font-medium text-gray-700">Time Period:</label>
        <select
          value={months}
          onChange={(e) => setMonths(Number(e.target.value))}
          className="border rounded px-3 py-1"
        >
          <option value={3}>Last 3 months</option>
          <option value={6}>Last 6 months</option>
          <option value={12}>Last 12 months</option>
        </select>
      </div>

      {/* Trend Summary */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white p-6 rounded-xl shadow-lg"
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-gray-800">Spending Trends</h2>
          <div className={`flex items-center space-x-2 ${trendDirection === 'up' ? 'text-red-600' : 'text-green-600'}`}>
            {trendDirection === 'up' ? <TrendingUp size={24} /> : <TrendingDown size={24} />}
            <span className="font-semibold">
              {trendPercentage.toFixed(1)}% {trendDirection === 'up' ? 'increase' : 'decrease'}
            </span>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={trendData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" />
            <YAxis />
            <Tooltip formatter={(value) => formatCurrency(Number(value ?? 0), currency)} />
            <Legend />
            <Line
              type="monotone"
              dataKey="total"
              stroke="#3b82f6"
              strokeWidth={3}
              dot={{ fill: '#3b82f6', r: 5 }}
              name="Total Spending"
            />
            <Line type="monotone" dataKey="income" stroke="#059669" strokeWidth={2} name="Recorded Income" />
          </LineChart>
        </ResponsiveContainer>
      </motion.div>

      {/* Monthly Comparison */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="bg-white p-6 rounded-xl shadow-lg"
      >
        <h2 className="text-2xl font-bold mb-4 text-gray-800">Monthly Spending</h2>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={trendData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" />
            <YAxis />
            <Tooltip formatter={(value) => formatCurrency(Number(value ?? 0), currency)} />
            <Bar dataKey="total" fill="#8b5cf6" name="Gross Expenses" />
            <Bar dataKey="income" fill="#10b981" name="Recorded Income" />
          </BarChart>
        </ResponsiveContainer>
      </motion.div>

      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-gradient-to-br from-blue-500 to-blue-600 text-white p-6 rounded-xl shadow-lg"
        >
          <p className="text-blue-100 text-sm mb-2">Average Monthly Spending</p>
          <p className="text-3xl font-bold">
            {formatCurrency(Math.round(trendData.reduce((sum: number, t) => sum + t.total, 0) / trendData.length), currency)}
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 }}
          className="bg-gradient-to-br from-purple-500 to-purple-600 text-white p-6 rounded-xl shadow-lg"
        >
          <p className="text-purple-100 text-sm mb-2">Highest Month</p>
          <p className="text-3xl font-bold">
            {formatCurrency(Math.max(...trendData.map((t) => t.total)), currency)}
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
          className="bg-gradient-to-br from-pink-500 to-pink-600 text-white p-6 rounded-xl shadow-lg"
        >
          <p className="text-pink-100 text-sm mb-2">Lowest Month</p>
          <p className="text-3xl font-bold">
            {formatCurrency(Math.min(...trendData.map((t) => t.total)), currency)}
          </p>
        </motion.div>
      </div>
    </div>
  )
}
