import { NextRequest, NextResponse } from 'next/server'
import { backendAuthRequest } from '@/lib/backend-auth'
import { SESSION_COOKIE, sessionCookieOptions } from '@/lib/auth'

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}))
  const backend = await backendAuthRequest('/api/auth/signup', body)
  const data = await backend.json().catch(() => ({ detail: 'Unable to create account' }))
  if (!backend.ok) return NextResponse.json(data, { status: backend.status })
  const response = NextResponse.json({ user: data.user }, { status: 201 })
  response.cookies.set(SESSION_COOKIE, data.token, sessionCookieOptions)
  return response
}
