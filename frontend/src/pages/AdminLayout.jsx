import { useEffect } from 'react'
import { Link, NavLink, Outlet, useMatch, useNavigate } from 'react-router-dom'
import { getToken, setToken } from '../api'
import { btnMutedClass, UserAreaLayout } from '../components/UserAreaLayout.jsx'

function headerNavClass({ isActive }) {
  return `rounded-lg px-3 py-2 text-sm font-semibold transition ${
    isActive ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-600 hover:bg-slate-100 hover:text-indigo-800'
  }`
}

export default function AdminLayout() {
  const nav = useNavigate()
  const templateWorkspace = useMatch({ path: '/admin/templates/:templateId', end: false })
  const fullBleed = Boolean(templateWorkspace)

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
    <UserAreaLayout
      centerContent={false}
      maxWidthClass="max-w-none"
      paddingClass="px-0"
      paddingYClass="py-0"
    >
      <div className="flex min-h-svh flex-1 flex-col">
        <header className="sticky top-0 z-40 flex shrink-0 flex-wrap items-center gap-2 border-b border-slate-200/90 bg-white/95 px-3 py-2.5 shadow-sm backdrop-blur-md sm:gap-4 sm:px-4">
          <Link to="/admin/templates" className="shrink-0 text-sm font-bold tracking-tight text-slate-900 sm:text-base">
            Admin
          </Link>
          <nav className="flex min-w-0 flex-1 flex-wrap items-center gap-1 sm:gap-2">
            <NavLink to="/admin/upload" className={headerNavClass}>
              Upload
            </NavLink>
            <NavLink to="/admin/templates" className={headerNavClass}>
              Templates
            </NavLink>
            <NavLink to="/admin/submissions" className={headerNavClass}>
              Filled forms
            </NavLink>
          </nav>
          <div className="ml-auto flex shrink-0 flex-wrap items-center justify-end gap-2">
            <Link
              to="/home"
              className="rounded-lg px-2.5 py-2 text-xs font-semibold text-indigo-600 hover:bg-indigo-50 sm:text-sm"
            >
              Site
            </Link>
            <button type="button" onClick={logout} className={`${btnMutedClass} !px-3 !py-2 text-xs sm:text-sm`}>
              Log out
            </button>
          </div>
        </header>

        <main
          className={
            fullBleed
              ? 'flex min-h-0 flex-1 flex-col overflow-hidden bg-slate-100/80'
              : 'flex w-full flex-1 flex-col px-3 py-5 sm:px-4 sm:py-6'
          }
        >
          {fullBleed ? (
            <div className="flex min-h-0 flex-1 flex-col">
              <Outlet />
            </div>
          ) : (
            <div className="rounded-2xl border border-slate-200/80 bg-white/90 p-5 shadow-sm sm:p-6 md:p-8">
              <Outlet />
            </div>
          )}
        </main>
      </div>
    </UserAreaLayout>
  )
}
