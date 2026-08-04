import { describe, expect, it } from 'vitest'

import { SESSION_COOKIE, sessionCookieOptions } from './auth'

describe('session cookie configuration', () => {
  it('uses a private strict same-site cookie', () => {
    expect(SESSION_COOKIE).toBe('finance_session')
    expect(sessionCookieOptions.httpOnly).toBe(true)
    expect(sessionCookieOptions.sameSite).toBe('strict')
    expect(sessionCookieOptions.path).toBe('/')
  })
})
