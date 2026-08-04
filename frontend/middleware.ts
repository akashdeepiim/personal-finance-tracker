import { NextRequest, NextResponse } from 'next/server'
import { SESSION_COOKIE } from '@/lib/auth'

export function middleware(request: NextRequest) {
  if (request.cookies.get(SESSION_COOKIE)?.value) return NextResponse.next()
  if (request.nextUrl.pathname.startsWith('/api/')) {
    return NextResponse.json({ detail: 'Authentication required' }, { status: 401 })
  }
  const loginUrl = new URL('/login', request.url)
  loginUrl.searchParams.set('next', request.nextUrl.pathname)
  return NextResponse.redirect(loginUrl)
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|login|signup|api/auth).*)'],
}
