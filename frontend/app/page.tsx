'use client'

import { useEffect, useState } from 'react'
import dynamic from 'next/dynamic'
import { motion } from 'framer-motion'
import CurrencySelector from '@/components/CurrencySelector'
import { Wallet, Upload, PieChart, TrendingUp, Brain, Clock, LogOut } from 'lucide-react'

const loadingView = () => <div className="flex h-64 items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" /></div>
const Dashboard = dynamic(() => import('@/components/Dashboard'), { loading: loadingView })
const UploadStatement = dynamic(() => import('@/components/UploadStatement'), { loading: loadingView })
const CategoriesView = dynamic(() => import('@/components/CategoriesView'), { loading: loadingView })
const TrendsView = dynamic(() => import('@/components/TrendsView'), { loading: loadingView })
const PsychologicalProfile = dynamic(() => import('@/components/PsychologicalProfile'), { loading: loadingView })
const TransactionTimeline = dynamic(() => import('@/components/TransactionTimeline'), { loading: loadingView })

export default function Home() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [refreshKey, setRefreshKey] = useState(0)
  const [selectedCurrency, setSelectedCurrency] = useState('INR')
  const [accountEmail, setAccountEmail] = useState('')

  useEffect(() => {
    fetch('/api/auth/me')
      .then(async (response) => {
        if (!response.ok) {
          window.location.assign('/login')
          return
        }
        const user = await response.json() as { email: string }
        setAccountEmail(user.email)
      })
      .catch(() => window.location.assign('/login'))
  }, [])

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: Wallet },
    { id: 'upload', label: 'Upload', icon: Upload },
    { id: 'timeline', label: 'Timeline', icon: Clock },
    { id: 'categories', label: 'Categories', icon: PieChart },
    { id: 'trends', label: 'Trends', icon: TrendingUp },
    { id: 'profile', label: 'Patterns', icon: Brain },
  ]

  const handleUploadSuccess = () => {
    setRefreshKey(prev => prev + 1)
    setActiveTab('dashboard')
  }

  const handleLogout = async () => {
    await fetch('/api/auth/logout', { method: 'POST' })
    window.location.assign('/login')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <motion.header
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="bg-white shadow-sm border-b border-gray-200"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              💰 Personal Finance Tracker
            </h1>
            <p className="text-gray-600 mt-1">Track, Analyze, and Optimize Your Spending</p>
          </div>
          <div className="flex items-center gap-2">
            {accountEmail && <span className="hidden max-w-48 truncate text-sm text-gray-600 md:block" title={accountEmail}>{accountEmail}</span>}
            <CurrencySelector selectedCurrency={selectedCurrency} onCurrencyChange={setSelectedCurrency} />
            <button onClick={handleLogout} title="Sign out" className="rounded-lg border bg-white p-2 text-gray-600 shadow-md hover:text-red-600">
              <LogOut size={20} />
            </button>
          </div>
        </div>
      </motion.header>

      {/* Navigation Tabs */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-6">
        <div className="flex space-x-2 overflow-x-auto pb-2">
          {tabs.map((tab) => {
            const Icon = tab.icon
            return (
              <motion.button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className={`
                  flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-all
                  ${activeTab === tab.id
                    ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg'
                    : 'bg-white text-gray-700 hover:bg-gray-100 shadow'
                  }
                `}
              >
                <Icon size={18} />
                <span>{tab.label}</span>
              </motion.button>
            )
          })}
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          {activeTab === 'dashboard' && <Dashboard key={refreshKey} currency={selectedCurrency} />}
          {activeTab === 'upload' && <UploadStatement onSuccess={handleUploadSuccess} />}
          {activeTab === 'timeline' && <TransactionTimeline key={refreshKey} currency={selectedCurrency} onUpdate={() => setRefreshKey(prev => prev + 1)} />}
          {activeTab === 'categories' && <CategoriesView key={refreshKey} currency={selectedCurrency} />}
          {activeTab === 'trends' && <TrendsView key={refreshKey} currency={selectedCurrency} />}
          {activeTab === 'profile' && <PsychologicalProfile key={refreshKey} currency={selectedCurrency} />}
        </motion.div>
      </main>
    </div>
  )
}
