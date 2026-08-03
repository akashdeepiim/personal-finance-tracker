const encoder = new TextEncoder()

export const SESSION_COOKIE = 'finance_session'

export function authConfigured() {
  return Boolean(process.env.FINANCE_APP_PASSWORD && process.env.FINANCE_SESSION_SECRET)
}

export async function sessionFor(password: string) {
  const secret = process.env.FINANCE_SESSION_SECRET || 'development-only'
  const key = await crypto.subtle.importKey(
    'raw', encoder.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'],
  )
  const signature = await crypto.subtle.sign('HMAC', key, encoder.encode(password))
  return Array.from(new Uint8Array(signature), byte => byte.toString(16).padStart(2, '0')).join('')
}

export function constantTimeEqual(left: string, right: string) {
  if (left.length !== right.length) return false
  let difference = 0
  for (let index = 0; index < left.length; index += 1) {
    difference |= left.charCodeAt(index) ^ right.charCodeAt(index)
  }
  return difference === 0
}

export async function validSession(value?: string) {
  if (!authConfigured()) return process.env.ENVIRONMENT !== 'production'
  const expected = await sessionFor(process.env.FINANCE_APP_PASSWORD!)
  return Boolean(value && constantTimeEqual(value, expected))
}
