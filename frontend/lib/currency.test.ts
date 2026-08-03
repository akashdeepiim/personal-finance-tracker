import { describe, expect, it } from 'vitest'

import { formatCurrency, getCurrencyIcon } from './currency'

describe('currency formatting', () => {
  it('formats fractional and zero-decimal currencies', () => {
    expect(formatCurrency(1234.5, 'USD')).toBe('$1,234.50')
    expect(formatCurrency(1234.5, 'JPY')).toBe('¥1,235')
  })

  it('falls back to the currency code', () => {
    expect(getCurrencyIcon('XYZ')).toBe('XYZ')
  })
})
