'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { getPsychologicalProfile } from '@/lib/api'
import { Brain, TrendingUp, AlertTriangle, CheckCircle, Target } from 'lucide-react'
import type { PsychologicalProfileData } from '@/lib/types'

interface PsychologicalProfileProps {
  currency?: string
}

export default function PsychologicalProfile({ currency = 'USD' }: PsychologicalProfileProps) {
  const [profile, setProfile] = useState<PsychologicalProfileData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadProfile = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const profileData = await getPsychologicalProfile(currency)
      setProfile(profileData)
    } catch (error) {
      console.error('Error loading profile:', error)
      setError('Spending patterns could not be loaded. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [currency])

  useEffect(() => { void loadProfile() }, [loadProfile])

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

  if (!profile || profile.message) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="text-center py-12"
      >
        <p className="text-gray-600 text-lg">{profile?.message || 'No profile data available. Upload statements to generate your profile!'}</p>
      </motion.div>
    )
  }

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'high': return 'text-red-600 bg-red-50'
      case 'medium': return 'text-yellow-600 bg-yellow-50'
      case 'low': return 'text-green-600 bg-green-50'
      default: return 'text-gray-600 bg-gray-50'
    }
  }

  return (
    <div className="space-y-6">
      {/* Main Profile Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-gradient-to-br from-purple-600 to-blue-600 text-white p-8 rounded-xl shadow-lg"
      >
        <div className="flex items-center space-x-4 mb-6">
          <div className="bg-white/20 p-4 rounded-full">
            <Brain size={32} />
          </div>
          <div>
            <h2 className="text-3xl font-bold">Spending Patterns</h2>
            <p className="text-purple-100 mt-1">Descriptive, rule-based observations from recent expenses</p>
          </div>
        </div>

        <div className="bg-white/10 backdrop-blur-sm p-6 rounded-lg">
          <h3 className="text-xl font-semibold mb-2">Observed pattern</h3>
          <p className="text-2xl font-bold">{profile.spending_personality || 'Analyzing...'}</p>
        </div>
      </motion.div>

      {/* Discretionary Spending Analysis */}
      {profile.impulse_indicators && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white p-6 rounded-xl shadow-lg"
        >
          <h3 className="text-xl font-bold mb-4 text-gray-800 flex items-center">
            <Target className="mr-2 text-blue-600" />
            Discretionary category share
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm text-gray-600 mb-1">Discretionary transactions</p>
              <p className="text-2xl font-bold text-gray-800">{profile.impulse_indicators.count}</p>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm text-gray-600 mb-1">Total Amount</p>
              <p className="text-2xl font-bold text-gray-800">
                {new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(profile.impulse_indicators.total)}
              </p>
            </div>
            <div className={`p-4 rounded-lg ${getRiskColor(profile.impulse_indicators.risk_level)}`}>
              <p className="text-sm mb-1">Share level</p>
              <p className="text-2xl font-bold capitalize">{profile.impulse_indicators.risk_level}</p>
            </div>
          </div>
          <div className="mt-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-600">Shopping, dining and entertainment share</span>
              <span className="text-sm font-semibold">{profile.impulse_indicators.percentage}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${profile.impulse_indicators.percentage}%` }}
                transition={{ duration: 1 }}
                className={`h-3 rounded-full ${profile.impulse_indicators.risk_level === 'high' ? 'bg-red-500' :
                  profile.impulse_indicators.risk_level === 'medium' ? 'bg-yellow-500' : 'bg-green-500'
                  }`}
              />
            </div>
          </div>
        </motion.div>
      )}

      {/* Financial Habits */}
      {profile.financial_habits && profile.financial_habits.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-white p-6 rounded-xl shadow-lg"
        >
          <h3 className="text-xl font-bold mb-4 text-gray-800 flex items-center">
            <TrendingUp className="mr-2 text-green-600" />
            Financial Habits
          </h3>
          <div className="space-y-2">
            {profile.financial_habits.map((habit: string, index: number) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className="flex items-center space-x-2 p-3 bg-gray-50 rounded-lg"
              >
                <CheckCircle size={20} className="text-green-600" />
                <span className="text-gray-700">{habit}</span>
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Risk Factors */}
      {profile.risk_factors && profile.risk_factors.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-white p-6 rounded-xl shadow-lg"
        >
          <h3 className="text-xl font-bold mb-4 text-gray-800 flex items-center">
            <AlertTriangle className="mr-2 text-orange-600" />
            Concentration checks
          </h3>
          <div className="space-y-2">
            {profile.risk_factors.map((risk: string, index: number) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className="flex items-center space-x-2 p-3 bg-orange-50 border-l-4 border-orange-500 rounded-lg"
              >
                <AlertTriangle size={20} className="text-orange-600" />
                <span className="text-gray-700">{risk}</span>
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Strengths */}
      {profile.strengths && profile.strengths.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="bg-white p-6 rounded-xl shadow-lg"
        >
          <h3 className="text-xl font-bold mb-4 text-gray-800 flex items-center">
            <CheckCircle className="mr-2 text-green-600" />
            Other observations
          </h3>
          <div className="space-y-2">
            {profile.strengths.map((strength: string, index: number) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className="flex items-center space-x-2 p-3 bg-green-50 border-l-4 border-green-500 rounded-lg"
              >
                <CheckCircle size={20} className="text-green-600" />
                <span className="text-gray-700">{strength}</span>
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Insights */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="bg-gradient-to-r from-blue-50 to-purple-50 p-6 rounded-xl border border-blue-200"
      >
        <h3 className="text-lg font-semibold text-gray-800 mb-3">How to read this</h3>
        <p className="text-sm text-gray-600">These are descriptive heuristics based only on imported transactions. They cannot determine intent, wellbeing, or whether a purchase was impulsive, and they are not financial or psychological advice.</p>
      </motion.div>
    </div>
  )
}
