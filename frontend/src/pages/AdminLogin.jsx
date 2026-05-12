import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { api, setToken } from '../api'
import PasswordField from '../components/PasswordField.jsx'
import {
  btnPrimaryClass,
  GlassCard,
  UserAreaLayout,
  userAreaInputClass,
} from '../components/UserAreaLayout.jsx'

export default function AdminLogin() {
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
      setToken(data.token)
      const role = data.user?.role
      if (role === 'admin') nav('/admin/upload')
      else if (role === 'user') nav('/user/forms')
      else setErr('This account has an unsupported role. Ask your administrator to fix it in the database.')
    } catch (ex) {
      setErr(ex.message)
    }
  }

  return (
    <UserAreaLayout>
      <div className="mb-8 text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-600">Administrator</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">Admin sign in</h1>
        <p className="mx-auto mt-3 max-w-md text-sm leading-relaxed text-slate-600">
          Manage templates and placeholders. Standard users are redirected to the forms app after login.
        </p>
      </div>

      <GlassCard>
        {banner && (
          <p className="mb-5 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2.5 text-sm text-emerald-900">
            {banner}
          </p>
        )}
        <form className="flex flex-col gap-5" onSubmit={onSubmit}>
          <label className="text-sm font-medium text-slate-800">
            Email
            <input
              type="email"
              autoComplete="username"
              className={userAreaInputClass}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="you@organization.com"
            />
          </label>
          <label className="text-sm font-medium text-slate-800">
            Password
            <PasswordField
              inputClassName={userAreaInputClass}
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="Your password"
            />
          </label>
          {err && (
            <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{err}</p>
          )}
          <button type="submit" className={`mt-1 ${btnPrimaryClass}`}>
            Sign in
          </button>
        </form>

        <p className="mt-8 text-center text-sm text-slate-600">
          <Link to="/signup" className="font-semibold text-indigo-600 hover:text-indigo-500">
            Create account
          </Link>
          <span className="text-slate-400"> · </span>
          <Link to="/user/login" className="font-semibold text-indigo-600 hover:text-indigo-500">
            User login
          </Link>
          <span className="text-slate-400"> · </span>
          <Link to="/" className="font-semibold text-indigo-600 hover:text-indigo-500">
            Home
          </Link>
        </p>
      </GlassCard>
    </UserAreaLayout>
  )
}
