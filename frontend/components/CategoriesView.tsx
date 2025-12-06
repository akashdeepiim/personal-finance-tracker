'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { getCategories, getTransactions } from '@/lib/api'
import { format } from 'date-fns'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'
import { formatCurrency } from '@/lib/currency'

const COLORS = ['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#ef4444', '#06b6d4', '#84cc16', '#f97316', '#6366f1']

interface CategoriesViewProps {
  currency?: string
}

export default function CategoriesView({ currency = 'USD' }: CategoriesViewProps) {
  const [categories, setCategories] = useState<any>(null)
  const [transactions, setTransactions] = useState<any[]>([])
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [currency])

  useEffect(() => {
    if (selectedCategory) {
      loadTransactions(selectedCategory)
    } else {
      loadTransactions()
    }
  }, [selectedCategory, currency])

  const loadData = async () => {
    setLoading(true)
    try {
      const [categoriesData, transactionsData] = await Promise.all([
        getCategories(),
        getTransactions(),
      ])
      setCategories(categoriesData)
      setTransactions(transactionsData)
    } catch (error) {
      console.error('Error loading data:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadTransactions = async (category?: string) => {
    try {
      const data = await getTransactions(undefined, undefined, category, currency)
      setTransactions(data)
    } catch (error) {
      console.error('Error loading transactions:', error)
    }
  }

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

  if (!categories || categories.categories.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="text-center py-12"
      >
        <p className="text-gray-600 text-lg">No categories found. Upload a statement to get started!</p>
      </motion.div>
    )
  }

  const categoryData = categories.categories.map((cat: any) => ({
    name: cat.name,
    value: cat.amount,
    percentage: cat.percentage,
  }))

  return (
    <div className="space-y-6">
      {/* Category Chart */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white p-6 rounded-xl shadow-lg"
      >
        <h2 className="text-2xl font-bold mb-6 text-gray-800">Spending by Category</h2>
        <ResponsiveContainer width="100%" height={400}>
          <PieChart>
            <Pie
              data={categoryData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percentage }) => `${name}: ${percentage.toFixed(1)}%`}
              outerRadius={120}
              fill="#8884d8"
              dataKey="value"
            >
              {categoryData.map((entry: any, index: number) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
              <Tooltip formatter={(value: number) => formatCurrency(value, currency)} />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </motion.div>

      {/* Category List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {categories.categories.map((cat: any, index: number) => (
          <motion.button
            key={cat.name}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
            onClick={() => setSelectedCategory(selectedCategory === cat.name ? null : cat.name)}
            className={`
              p-4 rounded-lg shadow text-left transition-all
              ${selectedCategory === cat.name
                ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white'
                : 'bg-white hover:shadow-lg'
              }
            `}
          >
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold">{cat.name}</h3>
              <div
                className="w-4 h-4 rounded-full"
                style={{ backgroundColor: COLORS[index % COLORS.length] }}
              />
            </div>
            <p className={`text-2xl font-bold ${selectedCategory === cat.name ? 'text-white' : 'text-gray-800'}`}>
              {formatCurrency(cat.amount, currency)}
            </p>
            <p className={`text-sm mt-1 ${selectedCategory === cat.name ? 'text-blue-100' : 'text-gray-600'}`}>
              {cat.percentage.toFixed(1)}% of total
            </p>
          </motion.button>
        ))}
      </div>

      {/* Transactions List */}
      {transactions.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white p-6 rounded-xl shadow-lg"
        >
          <h2 className="text-xl font-bold mb-4 text-gray-800">
            {selectedCategory ? `Transactions - ${selectedCategory}` : 'Recent Transactions'}
          </h2>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {transactions.slice(0, 50).map((transaction: any, index: number) => {
              const isIncome = transaction.transaction_type === 'credit'
              return (
                <motion.div
                  key={transaction.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.02 }}
                  className={`flex items-center justify-between p-3 rounded-lg hover:bg-gray-100 transition-colors ${
                    isIncome ? 'bg-green-50 border border-green-200' : 'bg-gray-50'
                  }`}
                >
                  <div className="flex-1">
                    <p className="font-medium text-gray-800">{transaction.description}</p>
                    <p className="text-sm text-gray-500">
                      {format(new Date(transaction.date), 'MMM dd, yyyy')} • 
                      <span className={`px-2 py-0.5 rounded text-xs ml-2 ${
                        isIncome ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                      }`}>
                        {transaction.category || 'Other'}
                      </span>
                    </p>
                  </div>
                  <p className={`text-lg font-semibold ${
                    isIncome ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {isIncome ? '+' : '-'}{formatCurrency(transaction.amount, currency)}
                  </p>
                </motion.div>
              )
            })}
          </div>
        </motion.div>
      )}
    </div>
  )
}

