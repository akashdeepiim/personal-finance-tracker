import axios from 'axios'

// All browser requests must use the same-origin proxy. The session token is
// intentionally HttpOnly and only the proxy can forward it to FastAPI.
const API_BASE = '/api/backend'

export const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const uploadStatement = async (file: File, accountType: string) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('account_type', accountType)

  // Use axios directly instead of 'api' instance to avoid default Content-Type header conflict
  const response = await axios.post(`${API_BASE}/api/upload-statement`, formData)
  return response.data
}

export const getTransactions = async (month?: number, year?: number, category?: string, currency?: string) => {
  const params: Record<string, string | number> = {}
  if (month) params.month = month
  if (year) params.year = year
  if (category) params.category = category
  if (currency) params.currency = currency

  const response = await api.get('/api/transactions', { params })
  return response.data
}

export const getCategories = async (currency?: string, month?: number, year?: number) => {
  const params: Record<string, string | number> = {}
  if (currency) params.currency = currency
  if (month) params.month = month
  if (year) params.year = year
  const response = await api.get('/api/categories', { params })
  return response.data
}

export const getAnalysis = async (year: number, month: number, currency?: string) => {
  const response = await api.get(`/api/analysis/${year}/${month}`, { params: { currency } })
  return response.data
}

export const getAnalysisPeriods = async () => {
  const response = await api.get('/api/analysis-periods')
  return response.data
}

export const getTrends = async (months: number = 6, currency?: string) => {
  const response = await api.get('/api/trends', { params: { months, currency } })
  return response.data
}

export const getPsychologicalProfile = async (currency?: string) => {
  const response = await api.get('/api/psychological-profile', { params: { currency } })
  return response.data
}

export const getCurrencyRates = async () => {
  const response = await api.get('/api/currency/rates')
  return response.data
}

export const convertCurrency = async (amount: number, fromCurrency: string, toCurrency: string) => {
  const response = await api.get('/api/currency/convert', {
    params: { amount, from_currency: fromCurrency, to_currency: toCurrency }
  })
  return response.data
}

export const getStatements = async () => {
  const response = await api.get('/api/statements')
  return response.data
}

export const deleteStatement = async (statementId: number) => {
  const response = await api.delete(`/api/statements/${statementId}`)
  return response.data
}

export const clearAllData = async () => {
  const response = await api.delete('/api/data/clear-all')
  return response.data
}

export const updateTransaction = async (
  transactionId: number,
  category?: string,
  subcategory?: string,
  transactionType?: string,
  applyToAllMatching: boolean = false
) => {
  const params = new URLSearchParams()
  if (category !== undefined && category !== null) params.append('category', category)
  if (subcategory !== undefined && subcategory !== null) params.append('subcategory', subcategory)
  if (transactionType !== undefined && transactionType !== null) params.append('transaction_type', transactionType)
  params.append('apply_to_all_matching', String(applyToAllMatching))

  const queryString = params.toString()
  const url = `/api/transactions/${transactionId}${queryString ? '?' + queryString : ''}`

  const response = await api.put(url)
  return response.data
}

export const getCategoryLearning = async () => {
  const response = await api.get('/api/category-learning')
  return response.data
}
