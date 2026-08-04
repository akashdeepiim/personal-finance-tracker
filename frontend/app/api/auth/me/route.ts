import { NextRequest, NextResponse } from 'next/server'
import { backendMeRequest } from '@/lib/backend-auth'
import { SESSION_COOKIE, sessionCookieOptions } from '@/lib/auth'

export async function GET(request: NextRequest) {
  const token = request.cookies.get(SESSION_COOKIE)?.value
  if (!token) return NextResponse.json({ detail: 'Authentication required' }, { status: 401 })
  const backend = await backendMeRequest(token)
  const data = await backend.json().catch(() => ({ detail: 'Authentication required' }))
  const response = NextResponse.json(data, { status: backend.status })
  if (backend.status === 401) response.cookies.set(SESSION_COOKIE, '', { ...sessionCookieOptions, maxAge: 0 })
  return response
}
