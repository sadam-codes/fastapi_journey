import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, setToken } from '../api'
import PasswordField from '../components/PasswordField.jsx'
import { toastError, toastSuccess } from '../toast.js'
import {
  btnPrimaryClass,
  GlassCard,
  UserAreaLayout,
  userAreaInputClass,
} from '../components/UserAreaLayout.jsx'

export default function Signup() {
  const nav = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setBusy(true)
    try {
      const data = await api('/auth/signup', {
        method: 'POST',
        body: { name, email, password },
      })
      if (data.token) setToken(data.token)
      toastSuccess('Welcome! Your account is ready.')
      nav('/user/forms')
    } catch (ex) {
      toastError(ex.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <UserAreaLayout>
      <div className="mb-8 text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-600">Join</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
          Create your account
        </h1>
        <p className="mx-auto mt-3 max-w-md text-sm leading-relaxed text-slate-600">
          You will sign in as a standard user. Organization admins can elevate access when
          needed.
        </p>
      </div>

      <GlassCard>
        <form className="flex flex-col gap-5" onSubmit={onSubmit}>
          <label className="text-sm font-medium text-slate-800">
            Full name
            <input
              className={userAreaInputClass}
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              autoComplete="name"
              placeholder="Jane Doe"
            />
          </label>
          <label className="text-sm font-medium text-slate-800">
            Email
            <input
              type="email"
              className={userAreaInputClass}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              placeholder="you@example.com"
            />
          </label>
          <label className="text-sm font-medium text-slate-800">
            Password
            <PasswordField
              inputClassName={userAreaInputClass}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="new-password"
              minLength={6}
              placeholder="At least 6 characters"
            />
          </label>
          <button type="submit" disabled={busy} className={`mt-1 ${btnPrimaryClass}`}>
            {busy ? 'Creating your account…' : 'Sign up'}
          </button>
        </form>

        <p className="mt-8 text-center text-sm text-slate-600">
          Already have an account?{' '}
          <Link to="/user/login" className="font-semibold text-indigo-600 hover:text-indigo-500">
            User login
          </Link>
          <span className="text-slate-400"> · </span>
          <Link to="/admin/login" className="font-semibold text-indigo-600 hover:text-indigo-500">
            Admin login
          </Link>
        </p>
      </GlassCard>

      <p className="mt-8 text-center text-sm text-slate-500">
        <Link to="/home" className="font-medium text-indigo-600 hover:text-indigo-500 hover:underline">
          ← Back to home
        </Link>
      </p>
    </UserAreaLayout>
  )
}
