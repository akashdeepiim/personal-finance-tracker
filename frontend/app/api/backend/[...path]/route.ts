import { NextRequest, NextResponse } from 'next/server'
import { SESSION_COOKIE, sessionCookieOptions } from '@/lib/auth'

const BACKEND_URL = process.env.BACKEND_API_URL || 'http://localhost:8000'
const API_TOKEN = process.env.FINANCE_API_TOKEN

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params
  const target = new URL(`/${path.join('/')}`, BACKEND_URL)
  target.search = request.nextUrl.search

  const headers = new Headers()
  const contentType = request.headers.get('content-type')
  if (contentType) headers.set('content-type', contentType)
  if (API_TOKEN) headers.set('authorization', `Bearer ${API_TOKEN}`)
  const sessionToken = request.cookies.get(SESSION_COOKIE)?.value
  if (sessionToken) headers.set('x-session-token', sessionToken)

  const response = await fetch(target, {
    method: request.method,
    headers,
    body: ['GET', 'HEAD'].includes(request.method) ? undefined : await request.arrayBuffer(),
    cache: 'no-store',
  })

  const outgoing = new NextResponse(response.body, {
    status: response.status,
    headers: { 'content-type': response.headers.get('content-type') || 'application/json' },
  })
  if (response.status === 401) {
    outgoing.cookies.set(SESSION_COOKIE, '', { ...sessionCookieOptions, maxAge: 0 })
  }
  return outgoing
}

export const GET = proxy
export const POST = proxy
export const PUT = proxy
export const DELETE = proxy
