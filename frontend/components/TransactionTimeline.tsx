'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { getTransactions, updateTransaction } from '@/lib/api'
import { format } from 'date-fns'
import { formatCurrency, getCurrencyIcon } from '@/lib/currency'
import { Edit2, Check, X, TrendingUp, TrendingDown } from 'lucide-react'

interface TransactionTimelineProps {
  currency?: string
  limit?: number
  onUpdate?: () => void
}

const CATEGORIES = [
  'Food & Dining', 'Shopping', 'Transportation', 'Bills & Utilities',
  'Entertainment', 'Healthcare', 'Education', 'Travel', 'Groceries',
  'Subscriptions', 'Income', 'Other'
]

export default function TransactionTimeline({ currency = 'USD', limit = 50, onUpdate }: TransactionTimelineProps) {
  const [transactions, setTransactions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editCategory, setEditCategory] = useState('')
  const [editType, setEditType] = useState<'debit' | 'credit'>('debit')

  useEffect(() => {
    loadTransactions()
  }, [currency])

  const loadTransactions = async () => {
    setLoading(true)
    try {
      const data = await getTransactions(undefined, undefined, undefined, currency)
      setTransactions(data.slice(0, limit))
    } catch (error) {
      console.error('Error loading transactions:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleEdit = (transaction: any) => {
    setEditingId(transaction.id)
    setEditCategory(transaction.category || 'Other')
    const txType = transaction.transaction_type || 'debit'
    setEditType(txType === 'credit' ? 'credit' : 'debit')
  }

  const handleSave = async (id: number) => {
    try {
      const result = await updateTransaction(id, editCategory, undefined, editType)
      setEditingId(null)
      setEditCategory('')
      // Reload transactions to get updated data
      await loadTransactions()
      // Notify parent component to refresh other views
      if (onUpdate) {
        onUpdate()
      }
    } catch (error: any) {
      console.error('Error updating transaction:', error)
      alert(error.response?.data?.detail || 'Failed to update transaction. Please try again.')
    }
  }

  const handleCancel = () => {
    setEditingId(null)
    setEditCategory('')
  }

  const groupByDate = (transactions: any[]) => {
    const grouped: { [key: string]: any[] } = {}
    transactions.forEach(t => {
      const dateKey = format(new Date(t.date), 'yyyy-MM-dd')
      if (!grouped[dateKey]) {
        grouped[dateKey] = []
      }
      grouped[dateKey].push(t)
    })
    return grouped
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

  const grouped = groupByDate(transactions)
  const sortedDates = Object.keys(grouped).sort().reverse()

  return (
    <div className="space-y-6">
      {sortedDates.map((dateKey, dateIndex) => {
        const dateTransactions = grouped[dateKey]
        const date = new Date(dateKey)
        
        return (
          <motion.div
            key={dateKey}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: dateIndex * 0.1 }}
            className="relative"
          >
            {/* Date Header */}
            <div className="flex items-center mb-4">
              <div className="flex-1 border-t border-gray-300"></div>
              <div className="px-4">
                <h3 className="text-lg font-semibold text-gray-700">
                  {format(date, 'EEEE, MMMM d, yyyy')}
                </h3>
                <p className="text-sm text-gray-500 text-center">
                  {dateTransactions.length} transaction{dateTransactions.length !== 1 ? 's' : ''}
                </p>
              </div>
              <div className="flex-1 border-t border-gray-300"></div>
            </div>

            {/* Timeline */}
            <div className="relative pl-8 border-l-2 border-blue-200 space-y-4">
              {dateTransactions.map((transaction, index) => {
                const isEditing = editingId === transaction.id
                const isIncome = transaction.transaction_type === 'credit'
                
                return (
                  <motion.div
                    key={transaction.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="relative"
                  >
                    {/* Timeline Dot */}
                    <div className={`absolute -left-11 w-4 h-4 rounded-full border-2 border-white ${
                      isIncome ? 'bg-green-500' : 'bg-red-500'
                    }`} />

                    {/* Transaction Card */}
                    <div className={`p-4 rounded-lg shadow-sm ${
                      isIncome ? 'bg-green-50 border border-green-200' : 'bg-white border border-gray-200'
                    }`}>
                      {isEditing ? (
                        <div className="space-y-3">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Category
                            </label>
                            <select
                              value={editCategory}
                              onChange={(e) => setEditCategory(e.target.value)}
                              className="w-full border rounded px-3 py-2"
                            >
                              {CATEGORIES.map(cat => (
                                <option key={cat} value={cat}>{cat}</option>
                              ))}
                            </select>
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Type
                            </label>
                            <div className="flex space-x-4">
                              <label className="flex items-center">
                                <input
                                  type="radio"
                                  value="debit"
                                  checked={editType === 'debit'}
                                  onChange={(e) => setEditType(e.target.value as 'debit' | 'credit')}
                                  className="mr-2"
                                />
                                <span className="text-gray-700">Expense</span>
                              </label>
                              <label className="flex items-center">
                                <input
                                  type="radio"
                                  value="credit"
                                  checked={editType === 'credit'}
                                  onChange={(e) => setEditType(e.target.value as 'debit' | 'credit')}
                                  className="mr-2"
                                />
                                <span className="text-gray-700">Income</span>
                              </label>
                            </div>
                          </div>
                          <div className="flex space-x-2">
                            <button
                              onClick={() => handleSave(transaction.id)}
                              className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center justify-center space-x-2"
                            >
                              <Check size={16} />
                              <span>Save</span>
                            </button>
                            <button
                              onClick={handleCancel}
                              className="flex-1 px-4 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400 flex items-center justify-center space-x-2"
                            >
                              <X size={16} />
                              <span>Cancel</span>
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center space-x-2 mb-1">
                              <h4 className="font-semibold text-gray-800">{transaction.description}</h4>
                              {isIncome ? (
                                <TrendingUp size={16} className="text-green-600" />
                              ) : (
                                <TrendingDown size={16} className="text-red-600" />
                              )}
                            </div>
                            <div className="flex items-center space-x-3 text-sm text-gray-600">
                              <span className={`px-2 py-1 rounded ${
                                isIncome ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                              }`}>
                                {transaction.category || 'Other'}
                              </span>
                              <span>{format(new Date(transaction.date), 'h:mm a')}</span>
                            </div>
                          </div>
                          <div className="flex items-center space-x-3">
                            <span className={`text-lg font-bold ${
                              isIncome ? 'text-green-600' : 'text-red-600'
                            }`}>
                              {isIncome ? '+' : '-'}{formatCurrency(transaction.amount, currency)}
                            </span>
                            <button
                              onClick={() => handleEdit(transaction)}
                              className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                              title="Edit category"
                            >
                              <Edit2 size={16} />
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  </motion.div>
                )
              })}
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}

