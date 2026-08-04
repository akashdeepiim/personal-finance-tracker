import { NextRequest, NextResponse } from 'next/server'
import { SESSION_COOKIE, sessionCookieOptions } from '@/lib/auth'
import { backendTarget } from '@/lib/backend-url'

const API_TOKEN = process.env.FINANCE_API_TOKEN

export const maxDuration = 300

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params
  try {
    const target = backendTarget(`/${path.join('/')}`)
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
  } catch (error) {
    console.error('Backend proxy request failed', error)
    return NextResponse.json(
      { detail: 'The backend service is temporarily unavailable' },
      { status: 503 },
    )
  }
}

export const GET = proxy
export const POST = proxy
export const PUT = proxy
export const DELETE = proxy
