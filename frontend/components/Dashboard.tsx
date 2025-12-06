'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { getAnalysis, getCategories, getTransactions } from '@/lib/api'
import { format } from 'date-fns'
import { TrendingUp, AlertCircle, CheckCircle } from 'lucide-react'
import { getCurrencyIcon } from '@/lib/currency'
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from 'recharts'
import { formatCurrency } from '@/lib/currency'

const COLORS = ['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#ef4444', '#06b6d4', '#84cc16']

interface DashboardProps {
  currency?: string
}

export default function Dashboard({ currency = 'USD' }: DashboardProps) {
  const [analysis, setAnalysis] = useState<any>(null)
  const [categories, setCategories] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1)
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear())

  useEffect(() => {
    loadData()
  }, [selectedMonth, selectedYear])

  const loadData = async () => {
    setLoading(true)
    try {
      const [analysisData, categoriesData] = await Promise.all([
        getAnalysis(selectedYear, selectedMonth),
        getCategories(currency),
      ])
      setAnalysis(analysisData)
      setCategories(categoriesData)
    } catch (error) {
      console.error('Error loading data:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [selectedMonth, selectedYear, currency])

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

  if (!analysis && !categories) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="text-center py-12"
      >
        <p className="text-gray-600 text-lg">No data available. Upload a statement to get started!</p>
      </motion.div>
    )
  }

  const categoryData = categories?.categories?.map((cat: any) => ({
    name: cat.name,
    value: cat.amount,
    percentage: cat.percentage,
  })) || []

  const recommendations = analysis?.savings_recommendations || []

  return (
    <div className="space-y-6">
      {/* Month Selector */}
      <div className="flex items-center space-x-4 bg-white p-4 rounded-lg shadow">
        <label className="text-sm font-medium text-gray-700">Month:</label>
        <select
          value={selectedMonth}
          onChange={(e) => setSelectedMonth(Number(e.target.value))}
          className="border rounded px-3 py-1"
        >
          {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
            <option key={m} value={m}>{format(new Date(2000, m - 1), 'MMMM')}</option>
          ))}
        </select>
        <label className="text-sm font-medium text-gray-700">Year:</label>
        <select
          value={selectedYear}
          onChange={(e) => setSelectedYear(Number(e.target.value))}
          className="border rounded px-3 py-1"
        >
          {Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - i).map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gradient-to-br from-blue-500 to-blue-600 text-white p-6 rounded-xl shadow-lg"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-blue-100 text-sm">Total Spending</p>
              <p className="text-3xl font-bold mt-2">
                {formatCurrency(analysis?.total_spending || 0, currency)}
              </p>
              {analysis?.total_income && (
                <p className="text-sm mt-1 text-blue-200">
                  Income: {formatCurrency(analysis.total_income, currency)}
                </p>
              )}
            </div>
            <span className="text-4xl opacity-80">{getCurrencyIcon(currency)}</span>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-gradient-to-br from-purple-500 to-purple-600 text-white p-6 rounded-xl shadow-lg"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-purple-100 text-sm">Categories</p>
              <p className="text-3xl font-bold mt-2">{categoryData.length}</p>
            </div>
            <TrendingUp size={40} className="opacity-80" />
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-gradient-to-br from-pink-500 to-pink-600 text-white p-6 rounded-xl shadow-lg"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-pink-100 text-sm">Potential Savings</p>
              <p className="text-3xl font-bold mt-2">
                {formatCurrency(recommendations.reduce((sum: number, r: any) => sum + (r.potential_savings || 0), 0), currency)}
              </p>
            </div>
            <AlertCircle size={40} className="opacity-80" />
          </div>
        </motion.div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Category Breakdown */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-white p-6 rounded-xl shadow-lg"
        >
          <h2 className="text-xl font-bold mb-4 text-gray-800">Category Breakdown</h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={categoryData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percentage }) => `${name}: ${percentage.toFixed(1)}%`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {categoryData.map((entry: any, index: number) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(value: number) => formatCurrency(value, currency)} />
            </PieChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Category Bar Chart */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 }}
          className="bg-white p-6 rounded-xl shadow-lg"
        >
          <h2 className="text-xl font-bold mb-4 text-gray-800">Spending by Category</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={categoryData}>
              <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
              <YAxis />
              <Tooltip formatter={(value: number) => formatCurrency(value, currency)} />
              <Bar dataKey="value" fill="#3b82f6" />
            </BarChart>
          </ResponsiveContainer>
        </motion.div>
      </div>

      {/* Savings Recommendations */}
      {recommendations.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white p-6 rounded-xl shadow-lg"
        >
          <h2 className="text-xl font-bold mb-4 text-gray-800 flex items-center">
            <AlertCircle className="mr-2 text-orange-500" />
            Savings Recommendations
          </h2>
          <div className="space-y-4">
            {recommendations.map((rec: any, index: number) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className={`p-4 rounded-lg border-l-4 ${
                  rec.severity === 'high' ? 'border-red-500 bg-red-50' : 'border-yellow-500 bg-yellow-50'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-800">{rec.category}</h3>
                    <p className="text-sm text-gray-600 mt-1">{rec.message}</p>
                    <div className="mt-2 flex items-center space-x-4 text-sm">
                      <span className="text-gray-600">
                        Current: {rec.current_percentage}%
                      </span>
                      <span className="text-gray-600">
                        Recommended: {rec.recommended_percentage}%
                      </span>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-green-600">
                      {formatCurrency(rec.potential_savings, currency)}
                    </p>
                    <p className="text-xs text-gray-500">potential savings</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  )
}

