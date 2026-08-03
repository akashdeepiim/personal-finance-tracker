'use client'

import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import { motion } from 'framer-motion'
import { getTransactions, updateTransaction } from '@/lib/api'
import { format } from 'date-fns'
import { formatCurrency } from '@/lib/currency'
import { Edit2, Check, X, TrendingUp, TrendingDown, ArrowRightLeft, RotateCcw } from 'lucide-react'
import type { Transaction } from '@/lib/types'

interface TransactionTimelineProps {
  currency?: string
  limit?: number
  onUpdate?: () => void
}

const CATEGORIES = [
  'Food & Dining', 'Shopping', 'Transportation', 'Bills & Utilities',
  'Entertainment', 'Healthcare', 'Education', 'Travel', 'Groceries',
  'Subscriptions', 'Income', 'Refunds', 'Transfers', 'Cash Withdrawal', 'Fees & Charges', 'Other'
]

export default function TransactionTimeline({ currency = 'USD', limit = 50, onUpdate }: TransactionTimelineProps) {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editCategory, setEditCategory] = useState('')
  const [editType, setEditType] = useState<Transaction['transaction_type']>('debit')
  const [applyToMatching, setApplyToMatching] = useState(false)

  const loadTransactions = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await getTransactions(undefined, undefined, undefined, currency)
      setTransactions(data.slice(0, limit))
    } catch (error) {
      console.error('Error loading transactions:', error)
      setError('Transactions could not be loaded. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [currency, limit])

  useEffect(() => { void loadTransactions() }, [loadTransactions])

  const handleEdit = (transaction: Transaction) => {
    setEditingId(transaction.id)
    setEditCategory(transaction.category || 'Other')
    const txType = transaction.transaction_type || 'debit'
    setEditType(txType)
    setApplyToMatching(false)
  }

  const handleSave = async (id: number) => {
    try {
      await updateTransaction(id, editCategory, undefined, editType, applyToMatching)
      setEditingId(null)
      setEditCategory('')
      // Reload transactions to get updated data
      await loadTransactions()
      // Notify parent component to refresh other views
      if (onUpdate) {
        onUpdate()
      }
    } catch (error: unknown) {
      console.error('Error updating transaction:', error)
      const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined
      alert(detail || 'Failed to update transaction. Please try again.')
    }
  }

  const handleCancel = () => {
    setEditingId(null)
    setEditCategory('')
  }

  const groupByDate = (transactions: Transaction[]) => {
    const grouped: Record<string, Transaction[]> = {}
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

  if (error) return <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">{error}</div>
  if (transactions.length === 0) return <p className="rounded-lg bg-blue-50 p-4 text-center text-gray-700">No transactions yet. Upload a statement to build your timeline.</p>

  const grouped = groupByDate(transactions)
  const sortedDates = Object.keys(grouped).sort().reverse()

  return (
    <div className="space-y-6">
      {sortedDates.map((dateKey, dateIndex) => {
        const dateTransactions = grouped[dateKey]
        const date = new Date(`${dateKey}T00:00:00`)
        
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
                const isRefund = transaction.transaction_type === 'refund'
                const isTransfer = transaction.transaction_type === 'transfer'
                const isPositive = isIncome || isRefund
                const tone = isTransfer ? 'slate' : isPositive ? 'green' : 'red'
                
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
                      tone === 'green' ? 'bg-green-500' : tone === 'slate' ? 'bg-slate-400' : 'bg-red-500'
                    }`} />

                    {/* Transaction Card */}
                    <div className={`p-4 rounded-lg shadow-sm ${
                      tone === 'green' ? 'bg-green-50 border border-green-200' : isTransfer ? 'bg-slate-50 border border-slate-200' : 'bg-white border border-gray-200'
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
                            <select value={editType} onChange={(event) => setEditType(event.target.value as Transaction['transaction_type'])} className="w-full rounded border px-3 py-2">
                              <option value="debit">Expense</option>
                              <option value="credit">Income</option>
                              <option value="refund">Refund</option>
                              <option value="transfer">Transfer / exclude from analysis</option>
                            </select>
                          </div>
                          <label className="flex items-start gap-2 rounded bg-blue-50 p-3 text-sm text-gray-700">
                            <input type="checkbox" checked={applyToMatching} onChange={(event) => setApplyToMatching(event.target.checked)} className="mt-1" />
                            <span>Apply this category to transactions from matching merchants. Leave off to change only this transaction.</span>
                          </label>
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
                              {isTransfer ? (
                                <ArrowRightLeft size={16} className="text-slate-600" />
                              ) : isRefund ? (
                                <RotateCcw size={16} className="text-green-600" />
                              ) : isIncome ? (
                                <TrendingUp size={16} className="text-green-600" />
                              ) : (
                                <TrendingDown size={16} className="text-red-600" />
                              )}
                            </div>
                            <div className="flex items-center space-x-3 text-sm text-gray-600">
                              <span className={`px-2 py-1 rounded ${
                                tone === 'green' ? 'bg-green-100 text-green-700' : tone === 'slate' ? 'bg-slate-200 text-slate-700' : 'bg-red-100 text-red-700'
                              }`}>
                                {transaction.category || 'Other'}
                              </span>
                              <span className="capitalize">{isTransfer ? 'excluded transfer' : isRefund ? 'refund' : isIncome ? 'income' : 'expense'}</span>
                            </div>
                          </div>
                          <div className="flex items-center space-x-3">
                            <span className={`text-lg font-bold ${
                              tone === 'green' ? 'text-green-600' : tone === 'slate' ? 'text-slate-600' : 'text-red-600'
                            }`}>
                              {isTransfer ? '' : isPositive ? '+' : '-'}{formatCurrency(transaction.amount, currency)}
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
