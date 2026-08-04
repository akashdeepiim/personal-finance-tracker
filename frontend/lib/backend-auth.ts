import 'server-only'

import { backendTarget, backendUnavailableResponse } from '@/lib/backend-url'

const API_TOKEN = process.env.FINANCE_API_TOKEN

export async function backendAuthRequest(path: string, body?: unknown, sessionToken?: string) {
  const headers = new Headers({ 'content-type': 'application/json' })
  if (API_TOKEN) headers.set('authorization', `Bearer ${API_TOKEN}`)
  if (sessionToken) headers.set('x-session-token', sessionToken)
  try {
    return await fetch(backendTarget(path), {
      method: 'POST',
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: 'no-store',
    })
  } catch (error) {
    console.error('Backend authentication request failed', error)
    return backendUnavailableResponse()
  }
}

export async function backendMeRequest(sessionToken: string) {
  const headers = new Headers()
  if (API_TOKEN) headers.set('authorization', `Bearer ${API_TOKEN}`)
  headers.set('x-session-token', sessionToken)
  try {
    return await fetch(backendTarget('/api/auth/me'), { headers, cache: 'no-store' })
  } catch (error) {
    console.error('Backend session request failed', error)
    return backendUnavailableResponse()
  }
}
