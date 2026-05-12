import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api, downloadSubmissionFile, getToken, setToken } from '../api'

export default function UserSubmissions() {
  const nav = useNavigate()
  const [params] = useSearchParams()
  const highlight = params.get('highlight')
  const [rows, setRows] = useState([])
  const [err, setErr] = useState('')

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
        setRows(await api('/forms/submissions'))
      } catch (e) {
        setErr(e.message)
      }
    })()
  }, [nav])

  return (
    <div className="px-5 py-8 sm:px-8">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
          My submissions
        </h1>
        <div className="flex flex-wrap gap-2">
          <Link
            to="/user/forms"
            className="rounded-lg border border-zinc-300 px-3 py-2 text-sm font-medium text-zinc-800 transition hover:bg-zinc-100 dark:border-zinc-600 dark:text-zinc-200 dark:hover:bg-zinc-800"
          >
            All forms
          </Link>
          <button
            type="button"
            onClick={logout}
            className="rounded-lg border border-zinc-300 bg-transparent px-3 py-2 text-sm font-medium text-zinc-800 transition hover:bg-zinc-100 dark:border-zinc-600 dark:text-zinc-200 dark:hover:bg-zinc-800"
          >
            Log out
          </button>
        </div>
      </header>
      {err && <p className="mt-4 text-sm text-red-600 dark:text-red-400">{err}</p>}
      {rows.length === 0 && !err ? (
        <p className="mt-6 text-sm text-zinc-500">No submissions yet.</p>
      ) : (
        <ul className="mt-6 space-y-2">
          {rows.map((r) => (
            <li
              key={r.id}
              className={`flex flex-wrap items-center justify-between gap-3 rounded-lg border border-zinc-200 px-4 py-3 dark:border-zinc-700 ${
                String(r.id) === highlight
                  ? 'border-violet-300 bg-violet-50/80 dark:border-violet-700 dark:bg-violet-950/40'
                  : ''
              }`}
            >
              <div>
                <p className="font-medium text-zinc-900 dark:text-zinc-100">{r.template_title}</p>
                <p className="text-xs text-zinc-500">{r.filled_filename}</p>
                <p className="text-xs text-zinc-400">{r.created_at}</p>
              </div>
              <button
                type="button"
                onClick={async () => {
                  try {
                    await downloadSubmissionFile(r.id, r.filled_filename)
                  } catch (e) {
                    alert(e.message)
                  }
                }}
                className="shrink-0 rounded-lg bg-violet-600 px-3 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-violet-700"
              >
                Download
              </button>
            </li>
          ))}
        </ul>
      )}
      <p className="mt-10 text-sm text-zinc-500">
        <Link to="/" className="text-violet-600 hover:underline dark:text-violet-400">
          Home
        </Link>
      </p>
    </div>
  )
}
