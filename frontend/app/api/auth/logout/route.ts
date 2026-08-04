import { NextRequest, NextResponse } from 'next/server'
import { backendAuthRequest } from '@/lib/backend-auth'
import { SESSION_COOKIE, sessionCookieOptions } from '@/lib/auth'

export async function POST(request: NextRequest) {
  const token = request.cookies.get(SESSION_COOKIE)?.value
  await backendAuthRequest('/api/auth/logout', undefined, token).catch(() => undefined)
  const response = NextResponse.json({ ok: true })
  response.cookies.set(SESSION_COOKIE, '', { ...sessionCookieOptions, maxAge: 0 })
  return response
}
