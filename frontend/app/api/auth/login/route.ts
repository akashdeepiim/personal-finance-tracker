import { NextRequest, NextResponse } from 'next/server'
import { authConfigured, constantTimeEqual, SESSION_COOKIE, sessionFor } from '@/lib/auth'

export async function POST(request: NextRequest) {
  if (!authConfigured()) {
    return process.env.ENVIRONMENT === 'production'
      ? NextResponse.json({ detail: 'Authentication is not configured' }, { status: 503 })
      : new NextResponse(null, { status: 204 })
  }
  const body = await request.json().catch(() => ({})) as { password?: string }
  const submitted = await sessionFor(body.password || '')
  const expected = await sessionFor(process.env.FINANCE_APP_PASSWORD!)
  if (!constantTimeEqual(submitted, expected)) {
    return NextResponse.json({ detail: 'Invalid password' }, { status: 401 })
  }
  const response = NextResponse.json({ ok: true })
  response.cookies.set(SESSION_COOKIE, expected, {
    httpOnly: true, sameSite: 'strict', secure: process.env.NODE_ENV === 'production',
    path: '/', maxAge: 60 * 60 * 12,
  })
  return response
}
