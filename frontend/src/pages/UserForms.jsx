import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, getToken, setToken } from '../api'
import { toastError } from '../toast.js'
import { GlassCard, UserAreaLayout, btnMutedClass, btnSecondaryClass } from '../components/UserAreaLayout.jsx'

export default function UserForms() {
  const nav = useNavigate()
  const [rows, setRows] = useState([])
  const [loadFailed, setLoadFailed] = useState(false)

  function logout() {
    setToken(null)
    nav('/user/login')
  }

  useEffect(() => {
    if (!getToken()) {
      nav('/user/login')
      return
    }
    ;(async () => {
      try {
        setLoadFailed(false)
        setRows(await api('/forms/templates'))
      } catch (e) {
        setLoadFailed(true)
        toastError(e.message)
      }
    })()
  }, [nav])

  return (
    <UserAreaLayout wide centerContent={false}>
      <div className="mb-6 text-center sm:mb-8 sm:text-left">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-600">Forms</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">Your forms</h1>
        <p className="mx-auto mt-2 max-w-xl text-sm text-slate-600 sm:mx-0">
          Pick a template to fill in. Download merged files from My submissions.
        </p>
      </div>

      <GlassCard className="p-0 sm:p-0">
        <div className="flex flex-col gap-4 border-b border-slate-200/80 p-6 sm:flex-row sm:items-center sm:justify-between sm:px-8 sm:py-6">
          <p className="text-sm font-medium text-slate-700">Available templates</p>
          <div className="flex flex-wrap gap-2">
            <Link to="/user/submissions" className={btnSecondaryClass}>
              My submissions
            </Link>
            <button type="button" onClick={logout} className={btnMutedClass}>
              Log out
            </button>
          </div>
        </div>

        <div className="p-6 sm:px-8 sm:pb-8 sm:pt-2">
          {rows.length === 0 && !loadFailed ? (
            <p className="mt-4 text-sm leading-relaxed text-slate-600">
              No templates available yet. Ask an admin to upload one.
            </p>
          ) : (
            <ul className="mt-2 divide-y divide-slate-200/90">
              {rows.map((r) => (
                <li key={r.id}>
                  <Link
                    to={`/user/forms/${r.id}`}
                    className="group block rounded-xl py-4 transition first:pt-2 hover:bg-indigo-50/60 sm:-mx-2 sm:px-2"
                  >
                    <span className="block font-semibold text-slate-900 group-hover:text-indigo-800">
                      {r.title}
                    </span>
                    <span className="mt-1 block text-sm text-slate-600">
                      {r.field_count} label{r.field_count === 1 ? '' : 's'} to fill
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </GlassCard>

      <p className="mt-8 text-center text-sm text-slate-500 sm:text-left">
        <Link to="/home" className="font-medium text-indigo-600 hover:text-indigo-500 hover:underline">
          ← Back to home
        </Link>
      </p>
    </UserAreaLayout>
  )
}
