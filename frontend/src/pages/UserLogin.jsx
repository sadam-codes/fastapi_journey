import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { api, setToken } from '../api'

const FILL_ROLES = ['client', 'paralegal', 'attorney']

export default function UserLogin() {
  const nav = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [banner, setBanner] = useState('')

  useEffect(() => {
    if (location.state?.registered) {
      setBanner('Account created. Sign in with your email and password.')
      nav(location.pathname, { replace: true, state: {} })
    }
  }, [location, nav])

  async function onSubmit(e) {
    e.preventDefault()
    setErr('')
    try {
      const data = await api('/auth/login', {
        method: 'POST',
        body: { email, password },
      })
      if (!FILL_ROLES.includes(data.user?.role)) {
        setErr('Use a client, paralegal, or attorney account here (not admin).')
        return
      }
      setToken(data.token)
      nav('/user/forms')
    } catch (ex) {
      setErr(ex.message)
    }
  }

  const inputClass =
    'mt-1.5 w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 shadow-sm outline-none ring-violet-500/40 focus:border-violet-500 focus:ring-2 dark:border-zinc-600 dark:bg-zinc-900 dark:text-zinc-100'

  return (
    <div className="mx-auto max-w-sm px-5 py-10 sm:px-8">
      <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
        User login
      </h1>
      {banner && (
        <p className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200">
          {banner}
        </p>
      )}
      <form className="mt-6 flex flex-col gap-4" onSubmit={onSubmit}>
        <label className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
          Email
          <input
            type="email"
            autoComplete="username"
            className={inputClass}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>
        <label className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
          Password
          <input
            type="password"
            autoComplete="current-password"
            className={inputClass}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        {err && <p className="text-sm text-red-600 dark:text-red-400">{err}</p>}
        <button
          type="submit"
          className="rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-violet-700 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:ring-offset-2 dark:focus:ring-offset-zinc-900"
        >
          Sign in
        </button>
      </form>
      <p className="mt-8 text-sm text-zinc-500">
        <Link to="/signup?role=client" className="text-violet-600 hover:underline dark:text-violet-400">
          Create user account
        </Link>
        {' · '}
        <Link to="/" className="text-violet-600 hover:underline dark:text-violet-400">
          Home
        </Link>
      </p>
    </div>
  )
}
