'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { ChevronDown } from 'lucide-react'
import { getCurrencyIcon } from '@/lib/currency'
import { getCurrencyRates } from '@/lib/api'

interface CurrencySelectorProps {
  selectedCurrency: string
  onCurrencyChange: (currency: string) => void
}

const CURRENCY_NAMES: { [key: string]: string } = {
  USD: 'US Dollar',
  EUR: 'Euro',
  GBP: 'British Pound',
  JPY: 'Japanese Yen',
  CAD: 'Canadian Dollar',
  AUD: 'Australian Dollar',
  CHF: 'Swiss Franc',
  CNY: 'Chinese Yuan',
  INR: 'Indian Rupee',
  MXN: 'Mexican Peso',
  BRL: 'Brazilian Real',
  ZAR: 'South African Rand',
  SGD: 'Singapore Dollar',
  HKD: 'Hong Kong Dollar',
  NZD: 'New Zealand Dollar',
}

export default function CurrencySelector({ selectedCurrency, onCurrencyChange }: CurrencySelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [currencies, setCurrencies] = useState<string[]>([])

  useEffect(() => {
    loadCurrencies()
  }, [])

  const loadCurrencies = async () => {
    try {
      const data = await getCurrencyRates()
      setCurrencies(data.supported_currencies || Object.keys(CURRENCY_NAMES))
    } catch (error) {
      // Fallback to default currencies
      setCurrencies(Object.keys(CURRENCY_NAMES))
    }
  }

  return (
    <div className="relative">
      <motion.button
        onClick={() => setIsOpen(!isOpen)}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        className="flex items-center space-x-2 px-4 py-2 bg-white rounded-lg shadow-md hover:shadow-lg transition-all border border-gray-200"
      >
        <span className="text-xl font-bold text-blue-600">{getCurrencyIcon(selectedCurrency)}</span>
        <span className="font-semibold text-gray-700">{selectedCurrency}</span>
        <ChevronDown 
          size={16} 
          className={`text-gray-500 transition-transform ${isOpen ? 'rotate-180' : ''}`}
        />
      </motion.button>

      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setIsOpen(false)}
          />
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="absolute right-0 mt-2 w-64 bg-white rounded-lg shadow-xl border border-gray-200 z-20 max-h-96 overflow-y-auto"
          >
            <div className="p-2">
              <div className="text-xs font-semibold text-gray-500 uppercase px-3 py-2">
                Select Currency
              </div>
              {currencies.map((currency) => (
                <button
                  key={currency}
                  onClick={() => {
                    onCurrencyChange(currency)
                    setIsOpen(false)
                  }}
                  className={`
                    w-full text-left px-3 py-2 rounded-lg transition-colors
                    ${selectedCurrency === currency
                      ? 'bg-blue-50 text-blue-600 font-semibold'
                      : 'hover:bg-gray-50 text-gray-700'
                    }
                  `}
                >
                  <div className="flex items-center justify-between">
                    <span>{currency}</span>
                    <span className="text-xs text-gray-500">
                      {CURRENCY_NAMES[currency] || currency}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </motion.div>
        </>
      )}
    </div>
  )
}

