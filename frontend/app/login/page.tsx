'use client'

import { FormEvent, useState } from 'react'

export default function LoginPage() {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setLoading(true)
    setError('')
    const response = await fetch('/api/auth/login', {
      method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ password }),
    })
    setLoading(false)
    if (response.ok) window.location.assign('/')
    else setError((await response.json().catch(() => ({}))).detail || 'Unable to sign in')
  }

  return (
    <main className="min-h-screen grid place-items-center bg-gradient-to-br from-blue-50 to-purple-50 p-4">
      <form onSubmit={submit} className="w-full max-w-sm rounded-xl bg-white p-8 shadow-lg">
        <h1 className="text-2xl font-bold text-gray-800">Personal Finance Tracker</h1>
        <p className="mt-2 text-sm text-gray-600">Enter your private access password.</p>
        <label className="mt-6 block text-sm font-medium text-gray-700" htmlFor="password">Password</label>
        <input id="password" type="password" required autoFocus value={password}
          onChange={(event) => setPassword(event.target.value)}
          className="mt-2 w-full rounded-lg border px-3 py-2" />
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        <button disabled={loading} className="mt-6 w-full rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white disabled:opacity-50">
          {loading ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </main>
  )
}
