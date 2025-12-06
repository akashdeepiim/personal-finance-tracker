'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import Dashboard from '@/components/Dashboard'
import UploadStatement from '@/components/UploadStatement'
import CategoriesView from '@/components/CategoriesView'
import TrendsView from '@/components/TrendsView'
import PsychologicalProfile from '@/components/PsychologicalProfile'
import TransactionTimeline from '@/components/TransactionTimeline'
import CurrencySelector from '@/components/CurrencySelector'
import { Wallet, Upload, PieChart, TrendingUp, Brain, Clock } from 'lucide-react'

const API_BASE = 'http://localhost:8000'

export default function Home() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [refreshKey, setRefreshKey] = useState(0)
  const [selectedCurrency, setSelectedCurrency] = useState('USD')

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: Wallet },
    { id: 'upload', label: 'Upload', icon: Upload },
    { id: 'timeline', label: 'Timeline', icon: Clock },
    { id: 'categories', label: 'Categories', icon: PieChart },
    { id: 'trends', label: 'Trends', icon: TrendingUp },
    { id: 'profile', label: 'Profile', icon: Brain },
  ]

  const handleUploadSuccess = () => {
    setRefreshKey(prev => prev + 1)
    setActiveTab('dashboard')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <motion.header
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="bg-white shadow-sm border-b border-gray-200"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              💰 Personal Finance Tracker
            </h1>
            <p className="text-gray-600 mt-1">Track, Analyze, and Optimize Your Spending</p>
          </div>
          <CurrencySelector 
            selectedCurrency={selectedCurrency}
            onCurrencyChange={setSelectedCurrency}
          />
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

