import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, getToken, setToken } from '../api'

export default function AdminDashboard() {
  const nav = useNavigate()
  const [title, setTitle] = useState('')
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')
  const [templates, setTemplates] = useState([])

  function logout() {
    setToken(null)
    nav('/admin/login')
  }

  async function loadList() {
    try {
      const rows = await api('/forms/admin/templates')
      setTemplates(rows)
    } catch {
      setTemplates([])
    }
  }

  useEffect(() => {
    if (!getToken()) {
      nav('/admin/login')
      return
    }
    loadList()
  }, [nav])

  async function onUpload(e) {
    e.preventDefault()
    setErr('')
    setMsg('')
    if (!file) {
      setErr('Choose a file first.')
      return
    }
    setBusy(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const base = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'
      const qs = title.trim() ? `?title=${encodeURIComponent(title.trim())}` : ''
      const res = await fetch(`${base}/forms/admin/upload${qs}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: fd,
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        const detail = data.detail
        const msgText = Array.isArray(detail)
          ? detail.map((d) => d.msg || JSON.stringify(d)).join(', ')
          : detail || res.statusText
        throw new Error(msgText)
      }
      setMsg(
        `${data.message} — ${data.fields_schema?.length || 0} field(s). Template #${data.id}`,
      )
      setFile(null)
      setTitle('')
      loadList()
    } catch (ex) {
      setErr(ex.message)
    } finally {
      setBusy(false)
    }
  }

  const inputClass =
    'mt-1.5 w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 shadow-sm outline-none ring-violet-500/40 focus:border-violet-500 focus:ring-2 dark:border-zinc-600 dark:bg-zinc-900 dark:text-zinc-100'

  return (
    <div className="px-5 py-8 sm:px-8">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
          Admin — upload template
        </h1>
        <button
          type="button"
          onClick={logout}
          className="rounded-lg border border-zinc-300 bg-transparent px-3 py-2 text-sm font-medium text-zinc-800 transition hover:bg-zinc-100 dark:border-zinc-600 dark:text-zinc-200 dark:hover:bg-zinc-800"
        >
          Log out
        </button>
      </header>

      <form
        className="mt-8 flex flex-col gap-4 rounded-xl border border-zinc-200 bg-zinc-50/50 p-5 dark:border-zinc-700 dark:bg-zinc-800/40"
        onSubmit={onUpload}
      >
        <label className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
          Display title (optional)
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Client intake 2026"
            className={inputClass}
          />
        </label>
        <label className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
          PDF, DOCX, or image
          <input
            type="file"
            accept=".pdf,.docx,.png,.jpg,.jpeg,.webp,.gif,.tiff,.bmp"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="mt-1.5 block w-full text-sm text-zinc-600 file:mr-4 file:rounded-lg file:border-0 file:bg-violet-600 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-violet-700 dark:text-zinc-400"
          />
        </label>
        {err && <p className="text-sm text-red-600 dark:text-red-400">{err}</p>}
        {msg && <p className="text-sm text-emerald-700 dark:text-emerald-400">{msg}</p>}
        <button
          type="submit"
          disabled={busy}
          className="rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-violet-700 disabled:opacity-60"
        >
          {busy ? 'Uploading…' : 'Upload & detect fields'}
        </button>
      </form>

      <section className="mt-8 rounded-xl border border-zinc-200 p-5 dark:border-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900 dark:text-zinc-100">Uploaded templates</h2>
        {templates.length === 0 ? (
          <p className="mt-3 text-sm text-zinc-500">No templates yet.</p>
        ) : (
          <ul className="mt-4 divide-y divide-zinc-200 dark:divide-zinc-700">
            {templates.map((t) => (
              <li key={t.id} className="py-3 text-sm">
                <span className="font-medium text-zinc-900 dark:text-zinc-100">{t.title}</span>
                <span className="text-zinc-600 dark:text-zinc-400"> — {t.original_filename} </span>
                <span className="text-zinc-500">
                  ({t.field_count} fields, id {t.id})
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <p className="mt-10 text-sm text-zinc-500">
        <Link to="/" className="text-violet-600 hover:underline dark:text-violet-400">
          Home
        </Link>
      </p>
    </div>
  )
}
