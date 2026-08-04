import 'server-only'

const BACKEND_URL = process.env.BACKEND_API_URL || 'http://localhost:8000'
const API_TOKEN = process.env.FINANCE_API_TOKEN

export async function backendAuthRequest(path: string, body?: unknown, sessionToken?: string) {
  const headers = new Headers({ 'content-type': 'application/json' })
  if (API_TOKEN) headers.set('authorization', `Bearer ${API_TOKEN}`)
  if (sessionToken) headers.set('x-session-token', sessionToken)
  return fetch(new URL(path, BACKEND_URL), {
    method: 'POST',
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: 'no-store',
  })
}

export async function backendMeRequest(sessionToken: string) {
  const headers = new Headers()
  if (API_TOKEN) headers.set('authorization', `Bearer ${API_TOKEN}`)
  headers.set('x-session-token', sessionToken)
  return fetch(new URL('/api/auth/me', BACKEND_URL), { headers, cache: 'no-store' })
}
