'use client'

import Link from 'next/link'
import { FormEvent, useState } from 'react'

export default function AuthForm({ mode }: { mode: 'login' | 'signup' }) {
  const signingUp = mode === 'signup'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (signingUp && password !== confirmation) {
      setError('Passwords do not match')
      return
    }
    setLoading(true)
    setError('')
    const response = await fetch(`/api/auth/${mode}`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    setLoading(false)
    if (response.ok) window.location.assign('/')
    else setError((await response.json().catch(() => ({}))).detail || 'Unable to continue')
  }

  return (
    <main className="grid min-h-screen place-items-center bg-gradient-to-br from-blue-50 to-purple-50 p-4">
      <form onSubmit={submit} className="w-full max-w-md rounded-xl bg-white p-8 shadow-lg">
        <h1 className="text-2xl font-bold text-gray-800">Personal Finance Tracker</h1>
        <p className="mt-2 text-sm text-gray-600">
          {signingUp ? 'Create a private account for your financial data.' : 'Sign in to your private account.'}
        </p>

        <label className="mt-6 block text-sm font-medium text-gray-700" htmlFor="email">Email</label>
        <input id="email" type="email" required autoFocus autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} className="mt-2 w-full rounded-lg border px-3 py-2" />

        <label className="mt-4 block text-sm font-medium text-gray-700" htmlFor="password">Password</label>
        <input id="password" type="password" required minLength={12} maxLength={128} autoComplete={signingUp ? 'new-password' : 'current-password'} value={password} onChange={(event) => setPassword(event.target.value)} className="mt-2 w-full rounded-lg border px-3 py-2" />
        {signingUp && <p className="mt-1 text-xs text-gray-500">Use at least 12 characters.</p>}

        {signingUp && <>
          <label className="mt-4 block text-sm font-medium text-gray-700" htmlFor="confirmation">Confirm password</label>
          <input id="confirmation" type="password" required minLength={12} maxLength={128} autoComplete="new-password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} className="mt-2 w-full rounded-lg border px-3 py-2" />
        </>}

        {error && <p role="alert" className="mt-3 text-sm text-red-600">{error}</p>}
        <button disabled={loading} className="mt-6 w-full rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white disabled:opacity-50">
          {loading ? 'Please wait…' : signingUp ? 'Create account' : 'Sign in'}
        </button>
        <p className="mt-5 text-center text-sm text-gray-600">
          {signingUp ? 'Already have an account?' : 'New here?'}{' '}
          <Link href={signingUp ? '/login' : '/signup'} className="font-semibold text-blue-600 hover:underline">
            {signingUp ? 'Sign in' : 'Create an account'}
          </Link>
        </p>
      </form>
    </main>
  )
}
