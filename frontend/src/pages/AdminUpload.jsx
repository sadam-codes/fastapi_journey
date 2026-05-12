import { useState } from 'react'
import { Link } from 'react-router-dom'
import { getToken } from '../api'
import {
  btnPrimaryClass,
  btnSecondaryClass,
  fileInputClass,
  userAreaInputClass,
} from '../components/UserAreaLayout.jsx'

export default function AdminUpload() {
  const [title, setTitle] = useState('')
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')

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
        `${data.message} — ${data.fields_schema?.length || 0} field(s) from {{…}} markers. Template #${data.id}`,
      )
      setFile(null)
      setTitle('')
    } catch (ex) {
      setErr(ex.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <h2 className="text-lg font-semibold text-slate-900">Upload template</h2>
      <p className="mt-2 text-sm text-slate-600">
        Only text wrapped in <code className="rounded bg-slate-100 px-1 font-mono text-xs">{'{{field_name}}'}</code>{' '}
        becomes a user form field. Download the file from the Templates tab to edit in Word, then upload again.
      </p>
      <form className="mt-6 flex max-w-xl flex-col gap-5" onSubmit={onUpload}>
        <label className="text-sm font-medium text-slate-800">
          Display title (optional)
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Client intake 2026"
            className={userAreaInputClass}
          />
        </label>
        <label className="text-sm font-medium text-slate-800">
          PDF, DOCX, or image
          <input
            type="file"
            accept=".pdf,.docx,.png,.jpg,.jpeg,.webp,.gif,.tiff,.bmp"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className={fileInputClass}
          />
        </label>
        {err && (
          <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{err}</p>
        )}
        {msg && (
          <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
            {msg}
          </p>
        )}
        <div className="flex flex-wrap gap-3">
          <button type="submit" disabled={busy} className={btnPrimaryClass}>
            {busy ? 'Uploading…' : 'Upload template'}
          </button>
          <Link to="/admin/templates" className={btnSecondaryClass}>
            Go to Templates
          </Link>
        </div>
      </form>
    </div>
  )
}
