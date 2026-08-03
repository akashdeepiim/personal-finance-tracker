import { NextRequest, NextResponse } from 'next/server'
import { SESSION_COOKIE, validSession } from '@/lib/auth'

export async function middleware(request: NextRequest) {
  if (await validSession(request.cookies.get(SESSION_COOKIE)?.value)) return NextResponse.next()
  if (request.nextUrl.pathname.startsWith('/api/')) {
    return NextResponse.json({ detail: 'Authentication required' }, { status: 401 })
  }
  return NextResponse.redirect(new URL('/login', request.url))
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|login|api/auth).*)'],
}
