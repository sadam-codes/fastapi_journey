import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api'

const ROLES = [
  { value: 'client', label: 'Client' },
  { value: 'paralegal', label: 'Paralegal' },
  { value: 'attorney', label: 'Attorney' },
  { value: 'admin', label: 'Admin' },
]

export default function Signup() {
  const nav = useNavigate()
  const [params] = useSearchParams()
  const qRole = params.get('role')?.toLowerCase().trim() || ''

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState(() =>
    ROLES.some((r) => r.value === qRole) ? qRole : 'client',
  )
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (ROLES.some((r) => r.value === qRole)) {
      setRole(qRole)
    }
  }, [qRole])

  async function onSubmit(e) {
    e.preventDefault()
    setErr('')
    setBusy(true)
    try {
      await api('/auth/signup', {
        method: 'POST',
        body: { name, email, password, role },
      })
      const loginPath = role === 'admin' ? '/admin/login' : '/user/login'
      nav(loginPath, { state: { registered: true } })
    } catch (ex) {
      setErr(ex.message)
    } finally {
      setBusy(false)
    }
  }

  const inputClass =
    'mt-1.5 w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 shadow-sm outline-none ring-violet-500/40 focus:border-violet-500 focus:ring-2 dark:border-zinc-600 dark:bg-zinc-900 dark:text-zinc-100'

  return (
    <div className="mx-auto max-w-sm px-5 py-10 sm:px-8">
      <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
        Create account
      </h1>
      <p className="mt-2 text-sm text-zinc-500">
        Choose your role, then sign in on the admin or user screen.
      </p>
      <form className="mt-6 flex flex-col gap-4" onSubmit={onSubmit}>
        <label className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
          Full name
          <input
            className={inputClass}
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            autoComplete="name"
          />
        </label>
        <label className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
          Email
          <input
            type="email"
            className={inputClass}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
        </label>
        <label className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
          Password
          <input
            type="password"
            className={inputClass}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="new-password"
            minLength={6}
          />
        </label>
        <label className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
          Role
          <select
            className={inputClass}
            value={role}
            onChange={(e) => setRole(e.target.value)}
          >
            {ROLES.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </label>
        {err && <p className="text-sm text-red-600 dark:text-red-400">{err}</p>}
        <button
          type="submit"
          disabled={busy}
          className="rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-violet-700 disabled:opacity-60"
        >
          {busy ? 'Creating…' : 'Sign up'}
        </button>
      </form>
      <p className="mt-8 text-sm text-zinc-500">
        Already have an account?{' '}
        <Link to="/admin/login" className="text-violet-600 hover:underline dark:text-violet-400">
          Admin login
        </Link>
        {' · '}
        <Link to="/user/login" className="text-violet-600 hover:underline dark:text-violet-400">
          User login
        </Link>
        {' · '}
        <Link to="/" className="text-violet-600 hover:underline dark:text-violet-400">
          Home
        </Link>
      </p>
    </div>
  )
}
