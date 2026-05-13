import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api, downloadSubmissionFile, getToken, setToken } from '../api'
import { toastError, toastSuccess } from '../toast.js'
import {
  btnMutedClass,
  btnPrimaryClass,
  btnSecondaryClass,
  GlassCard,
  UserAreaLayout,
} from '../components/UserAreaLayout.jsx'

export default function UserSubmissions() {
  const nav = useNavigate()
  const [params] = useSearchParams()
  const highlight = params.get('highlight')
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
        setRows(await api('/forms/submissions'))
      } catch (e) {
        setLoadFailed(true)
        toastError(e.message)
      }
    })()
  }, [nav])

  return (
    <UserAreaLayout wide centerContent={false}>
      <div className="mb-6 text-center sm:mb-8 sm:text-left">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-600">Downloads</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">My submissions</h1>
        <p className="mx-auto mt-2 max-w-xl text-sm text-slate-600 sm:mx-0">
          Every completed form appears here. Download the merged file whenever you need it.
        </p>
      </div>

      <GlassCard className="p-0 sm:p-0">
        <div className="flex flex-col gap-4 border-b border-slate-200/80 p-6 sm:flex-row sm:items-center sm:justify-between sm:px-8 sm:py-6">
          <p className="text-sm font-medium text-slate-700">Your merged files</p>
          <div className="flex flex-wrap gap-2">
            <Link to="/user/forms" className={btnSecondaryClass}>
              All forms
            </Link>
            <button type="button" onClick={logout} className={btnMutedClass}>
              Log out
            </button>
          </div>
        </div>

        <div className="p-6 sm:px-8 sm:pb-8 sm:pt-2">
          {rows.length === 0 && !loadFailed ? (
            <p className="mt-4 text-sm leading-relaxed text-slate-600">
              No submissions yet. Open a form from{' '}
              <Link to="/user/forms" className="font-semibold text-indigo-600 hover:text-indigo-500">
                Your forms
              </Link>{' '}
              and submit answers to generate a file here.
            </p>
          ) : (
            <ul className="mt-2 space-y-3">
              {rows.map((r) => {
                const isHi = String(r.id) === highlight
                return (
                  <li key={r.id}>
                    <div
                      className={`flex flex-col gap-4 rounded-xl border px-4 py-4 transition sm:flex-row sm:items-center sm:justify-between sm:px-5 ${
                        isHi
                          ? 'border-indigo-300 bg-indigo-50/70 shadow-sm ring-1 ring-indigo-200/60'
                          : 'border-slate-200/90 bg-white/60 hover:border-indigo-200/80 hover:bg-indigo-50/40'
                      }`}
                    >
                      <div className="min-w-0 flex-1">
                        <p className="font-semibold text-slate-900">{r.template_title}</p>
                        <p className="mt-1 truncate text-sm text-slate-600" title={r.filled_filename}>
                          {r.filled_filename}
                        </p>
                        <p className="mt-1 text-xs font-medium uppercase tracking-wide text-slate-400">
                          {r.created_at}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={async () => {
                          try {
                            await downloadSubmissionFile(r.id, r.filled_filename)
                            toastSuccess('Download started.')
                          } catch (e) {
                            toastError(e.message || 'Download failed.')
                          }
                        }}
                        className={`shrink-0 ${btnPrimaryClass} py-2.5 shadow-md`}
                      >
                        Download
                      </button>
                    </div>
                  </li>
                )
              })}
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
