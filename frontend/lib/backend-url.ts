import 'server-only'

const configuredUrl =
  process.env.BACKEND_API_URL || process.env.NEXT_PUBLIC_API_URL

export function backendTarget(path: string): URL {
  const fallback = process.env.NODE_ENV === 'production' ? undefined : 'http://localhost:8000'
  const baseUrl = configuredUrl || fallback
  if (!baseUrl) {
    throw new Error('BACKEND_API_URL is not configured')
  }

  const parsed = new URL(baseUrl)
  if (!['http:', 'https:'].includes(parsed.protocol)) {
    throw new Error('BACKEND_API_URL must be an absolute HTTP(S) URL')
  }
  return new URL(path, parsed)
}

export function backendUnavailableResponse(): Response {
  return Response.json(
    { detail: 'The backend service is temporarily unavailable' },
    { status: 503 },
  )
}
