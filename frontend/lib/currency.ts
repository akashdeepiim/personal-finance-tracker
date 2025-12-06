export const formatCurrency = (amount: number, currency: string = 'USD'): string => {
  const symbols: { [key: string]: string } = {
    USD: '$',
    EUR: '€',
    GBP: '£',
    JPY: '¥',
    CAD: 'C$',
    AUD: 'A$',
    CHF: 'CHF',
    CNY: '¥',
    INR: '₹',
    MXN: '$',
    BRL: 'R$',
    ZAR: 'R',
    SGD: 'S$',
    HKD: 'HK$',
    NZD: 'NZ$',
  }

  const symbol = symbols[currency.toUpperCase()] || currency.toUpperCase()

  // Format based on currency
  if (['JPY', 'KRW'].includes(currency.toUpperCase())) {
    return `${symbol}${amount.toLocaleString('en-US', { maximumFractionDigits: 0 })}`
  } else {
    return `${symbol}${amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }
}

export const getCurrencyIcon = (currency: string = 'USD'): string => {
  const icons: { [key: string]: string } = {
    USD: '$',
    EUR: '€',
    GBP: '£',
    JPY: '¥',
    CAD: 'C$',
    AUD: 'A$',
    CHF: 'CHF',
    CNY: '¥',
    INR: '₹',
    MXN: '$',
    BRL: 'R$',
    ZAR: 'R',
    SGD: 'S$',
    HKD: 'HK$',
    NZD: 'NZ$',
  }
  return icons[currency.toUpperCase()] || currency.toUpperCase()
}
