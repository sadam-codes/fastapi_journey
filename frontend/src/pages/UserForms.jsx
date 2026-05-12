import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, getToken, setToken } from '../api'

export default function UserForms() {
  const nav = useNavigate()
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
        setRows(await api('/forms/templates'))
      } catch (e) {
        setErr(e.message)
      }
    })()
  }, [nav])

  return (
    <div className="px-5 py-8 sm:px-8">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
          Your forms
        </h1>
        <div className="flex flex-wrap gap-2">
          <Link
            to="/user/submissions"
            className="rounded-lg border border-zinc-300 px-3 py-2 text-sm font-medium text-zinc-800 transition hover:bg-zinc-100 dark:border-zinc-600 dark:text-zinc-200 dark:hover:bg-zinc-800"
          >
            My submissions
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
        <p className="mt-6 text-sm text-zinc-500">
          No templates available yet. Ask an admin to upload one.
        </p>
      ) : (
        <ul className="mt-6 divide-y divide-zinc-200 dark:divide-zinc-700">
          {rows.map((r) => (
            <li key={r.id}>
              <Link
                to={`/user/forms/${r.id}`}
                className="block py-4 transition hover:bg-violet-50/50 dark:hover:bg-violet-950/20"
              >
                <span className="block font-medium text-zinc-900 dark:text-zinc-100">{r.title}</span>
                <span className="mt-0.5 block text-sm text-zinc-500">
                  {r.original_filename} — {r.field_count} fields
                </span>
              </Link>
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
