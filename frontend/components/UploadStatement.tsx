'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { uploadStatement, getStatements, deleteStatement, clearAllData } from '@/lib/api'
import { Upload, FileText, CheckCircle, AlertCircle, Trash2, AlertTriangle } from 'lucide-react'
import axios from 'axios'
import type { Statement } from '@/lib/types'

interface UploadStatementProps {
  onSuccess: () => void
}

export default function UploadStatement({ onSuccess }: UploadStatementProps) {
  const [file, setFile] = useState<File | null>(null)
  const [accountType, setAccountType] = useState('credit_card')
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null)
  const [statements, setStatements] = useState<Statement[]>([])
  const [loadingStatements, setLoadingStatements] = useState(true)

  useEffect(() => {
    loadStatements()
  }, [])

  const loadStatements = async () => {
    setLoadingStatements(true)
    try {
      const data = await getStatements()
      setStatements(data)
    } catch (error) {
      console.error('Error loading statements:', error)
    } finally {
      setLoadingStatements(false)
    }
  }

  const handleDelete = async (statementId: number) => {
    const confirmed = confirm(
      '⚠️ Are you sure you want to delete this statement?\n\n' +
      'This will permanently delete the statement and ALL its transactions. This action cannot be undone.'
    )
    
    if (!confirmed) {
      return
    }

    try {
      const result = await deleteStatement(statementId)
      await loadStatements()
      onSuccess() // Refresh other views
      alert(`✅ Successfully deleted statement and ${result.deleted_transactions || 0} transactions.`)
    } catch (error: unknown) {
      console.error('Delete error:', error)
      const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined
      alert(detail || 'Failed to delete statement. Please try again.')
    }
  }

  const handleClearAll = async () => {
    const confirmed = confirm(
      '⚠️ WARNING: This will delete ALL uploaded statements, transactions, and analyses.\n\n' +
      'This action cannot be undone. Are you absolutely sure?'
    )
    
    if (!confirmed) {
      return
    }

    // Double confirmation
    const doubleConfirm = confirm('Are you REALLY sure? This will permanently delete all your data.')
    if (!doubleConfirm) {
      return
    }

    try {
      await clearAllData()
      await loadStatements()
      onSuccess() // Refresh other views
      alert('All data has been cleared successfully.')
    } catch (error: unknown) {
      const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined
      alert(detail || 'Failed to clear all data')
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
      setResult(null)
    }
  }

  const handleUpload = async () => {
    if (!file) {
      setResult({ success: false, message: 'Please select a file' })
      return
    }

    setUploading(true)
    setResult(null)

    try {
      const response = await uploadStatement(file, accountType)
      setResult({
        success: true,
        message: `Successfully uploaded! Found ${response.transactions_count} transactions.`,
      })
      setFile(null)
      await loadStatements()
      onSuccess()
    } catch (error: unknown) {
      const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined
      setResult({
        success: false,
        message: detail || 'Upload failed. Please try again.',
      })
    } finally {
      setUploading(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-2xl mx-auto"
    >
      <div className="bg-white rounded-xl shadow-lg p-8">
        <h2 className="text-2xl font-bold mb-6 text-gray-800">Upload Statement</h2>

        {/* Account Type Selection */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Account Type
          </label>
          <div className="flex space-x-4">
            <label className="flex items-center cursor-pointer">
              <input
                type="radio"
                value="credit_card"
                checked={accountType === 'credit_card'}
                onChange={(e) => setAccountType(e.target.value)}
                className="mr-2"
              />
              <span className="text-gray-700">Credit Card</span>
            </label>
            <label className="flex items-center cursor-pointer">
              <input
                type="radio"
                value="bank_account"
                checked={accountType === 'bank_account'}
                onChange={(e) => setAccountType(e.target.value)}
                className="mr-2"
              />
              <span className="text-gray-700">Bank Account</span>
            </label>
          </div>
          <p className="mt-2 text-xs text-gray-500">Choose carefully: bank deposits are treated as inflows, while credit-card payments and refunds are credits that should not be counted as income.</p>
        </div>

        {/* File Upload Area */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select Statement File
          </label>
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-500 transition-colors">
            <input
              type="file"
              accept=".pdf,.csv"
              onChange={handleFileChange}
              className="hidden"
              id="file-upload"
            />
            <label htmlFor="file-upload" className="cursor-pointer">
              <motion.div
                whileHover={{ scale: 1.05 }}
                className="flex flex-col items-center"
              >
                <Upload size={48} className="text-gray-400 mb-4" />
                <p className="text-gray-600 mb-2">
                  Click to select a statement
                </p>
                <p className="text-sm text-gray-500">
                  PDF or CSV files only
                </p>
              </motion.div>
            </label>
          </div>

          {file && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-4 flex items-center space-x-2 bg-blue-50 p-3 rounded-lg"
            >
              <FileText className="text-blue-600" size={20} />
              <span className="text-sm text-gray-700">{file.name}</span>
              <span className="text-xs text-gray-500">
                ({(file.size / 1024).toFixed(2)} KB)
              </span>
            </motion.div>
          )}
        </div>

        {/* Upload Button */}
        <button
          onClick={handleUpload}
          disabled={!file || uploading}
          className={`
            w-full py-3 px-6 rounded-lg font-semibold text-white
            transition-all duration-200
            ${!file || uploading
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 shadow-lg hover:shadow-xl'
            }
          `}
        >
          {uploading ? (
            <span className="flex items-center justify-center">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                className="w-5 h-5 border-2 border-white border-t-transparent rounded-full mr-2"
              />
              Uploading...
            </span>
          ) : (
            'Upload Statement'
          )}
        </button>

        {/* Result Message */}
        {result && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`mt-4 p-4 rounded-lg flex items-center space-x-2 ${
              result.success
                ? 'bg-green-50 text-green-800'
                : 'bg-red-50 text-red-800'
            }`}
          >
            {result.success ? (
              <CheckCircle size={20} />
            ) : (
              <AlertCircle size={20} />
            )}
            <span>{result.message}</span>
          </motion.div>
        )}

        {/* Instructions */}
        <div className="mt-8 p-4 bg-gray-50 rounded-lg">
          <h3 className="font-semibold text-gray-800 mb-2">Supported Formats:</h3>
          <ul className="text-sm text-gray-600 space-y-1">
            <li>• PDF statements from banks and credit card companies</li>
            <li>• CSV files with Date, Amount, and Description columns</li>
            <li>• Categories and cash-flow types are suggested automatically; review refunds and transfers in Timeline</li>
          </ul>
        </div>
      </div>

      {/* Uploaded Statements */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mt-8 bg-white rounded-xl shadow-lg p-6"
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-800">Uploaded Statements</h2>
          {statements.length > 0 && (
            <button
              onClick={handleClearAll}
              className="flex items-center space-x-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm font-medium"
            >
              <AlertTriangle size={16} />
              <span>Clear All Data</span>
            </button>
          )}
        </div>
        {loadingStatements ? (
          <div className="text-center py-4">
            <p className="text-gray-600">Loading...</p>
          </div>
        ) : statements.length === 0 ? (
          <div className="text-center py-8">
            <FileText className="mx-auto text-gray-400 mb-2" size={48} />
            <p className="text-gray-600">No statements uploaded yet</p>
          </div>
        ) : (
          <div className="space-y-3">
            {statements.map((statement) => (
              <motion.div
                key={statement.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors border border-gray-200"
              >
                <div className="flex items-center space-x-4 flex-1">
                  <FileText className="text-blue-600" size={24} />
                  <div>
                    <p className="font-semibold text-gray-800">{statement.filename}</p>
                    <p className="text-sm text-gray-600">
                      {statement.account_type.replace('_', ' ')} • {statement.currency} • 
                      {' '}{new Date(statement.upload_date).toLocaleDateString()} • 
                      {' '}{statement.transaction_count} transaction{statement.transaction_count !== 1 ? 's' : ''}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(statement.id)}
                  className="flex items-center space-x-2 px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors border border-red-200"
                  title="Delete statement and all transactions"
                >
                  <Trash2 size={18} />
                  <span className="text-sm font-medium">Delete</span>
                </button>
              </motion.div>
            ))}
          </div>
        )}
      </motion.div>
    </motion.div>
  )
}
