import { describe, expect, it } from 'vitest'

import { constantTimeEqual } from './auth'

describe('session comparison', () => {
  it('accepts equal values and rejects unequal values', () => {
    expect(constantTimeEqual('abc', 'abc')).toBe(true)
    expect(constantTimeEqual('abc', 'abd')).toBe(false)
    expect(constantTimeEqual('abc', 'ab')).toBe(false)
  })
})
