import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import { getToken, setToken } from '../api'
import { btnMutedClass, UserAreaLayout } from '../components/UserAreaLayout.jsx'

function tabClass({ isActive }) {
  return `rounded-t-lg px-4 py-2.5 text-sm font-semibold transition ${
    isActive
      ? 'border border-b-0 border-slate-200/90 bg-white/95 text-indigo-700 shadow-sm'
      : 'border border-transparent text-slate-600 hover:text-indigo-600'
  }`
}

export default function AdminLayout() {
  const nav = useNavigate()

  useEffect(() => {
    if (!getToken()) {
      nav('/admin/login', { replace: true })
    }
  }, [nav])

  function logout() {
    setToken(null)
    nav('/admin/login')
  }

  if (!getToken()) {
    return (
      <div className="flex min-h-svh items-center justify-center text-sm text-slate-600">Redirecting…</div>
    )
  }

  return (
    <UserAreaLayout wide centerContent={false}>
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="text-center sm:text-left">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-600">Dashboard</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">Admin</h1>
          <p className="mt-2 max-w-xl text-sm text-slate-600">
            Upload on one tab; manage templates, preview, download to edit, and delete on the other.
          </p>
        </div>
        <button type="button" onClick={logout} className={`self-center sm:self-auto ${btnMutedClass}`}>
          Log out
        </button>
      </div>

      <div className="flex flex-wrap gap-1 rounded-t-xl border border-b-0 border-slate-200/80 bg-slate-100/50 p-1 sm:inline-flex">
        <NavLink to="/admin/upload" className={tabClass} end>
          Upload
        </NavLink>
        <NavLink to="/admin/templates" className={tabClass}>
          Templates
        </NavLink>
      </div>

      <div className="rounded-b-xl border border-t-0 border-slate-200/80 bg-white/80 p-6 shadow-sm sm:p-8">
        <Outlet />
      </div>

      <p className="mt-8 text-center text-sm text-slate-500 sm:text-left">
        <Link to="/" className="font-medium text-indigo-600 hover:text-indigo-500 hover:underline">
          ← Back to home
        </Link>
      </p>
    </UserAreaLayout>
  )
}
