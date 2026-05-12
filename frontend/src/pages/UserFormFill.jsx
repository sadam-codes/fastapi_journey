import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, getToken } from '../api'

export default function UserFormFill() {
  const { id } = useParams()
  const nav = useNavigate()
  const [detail, setDetail] = useState(null)
  const [answers, setAnswers] = useState({})
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!getToken()) {
      nav('/user/login')
      return
    }
    ;(async () => {
      try {
        const d = await api(`/forms/templates/${id}`)
        setDetail(d)
        const init = {}
        for (const f of d.fields_schema || []) {
          init[f.key] = ''
        }
        setAnswers(init)
      } catch (e) {
        setErr(e.message)
      }
    })()
  }, [id, nav])

  function setField(key, v) {
    setAnswers((a) => ({ ...a, [key]: v }))
  }

  async function onSubmit(e) {
    e.preventDefault()
    setErr('')
    setBusy(true)
    try {
      const res = await api(`/forms/templates/${id}/submit`, {
        method: 'POST',
        body: { answers },
      })
      nav(`/user/submissions?highlight=${res.submission_id}`)
    } catch (ex) {
      setErr(ex.message)
    } finally {
      setBusy(false)
    }
  }

  const inputClass =
    'mt-1.5 w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 shadow-sm outline-none ring-violet-500/40 focus:border-violet-500 focus:ring-2 dark:border-zinc-600 dark:bg-zinc-900 dark:text-zinc-100'

  if (!detail && !err) {
    return (
      <div className="px-5 py-10 sm:px-8">
        <p className="text-sm text-zinc-500">Loading…</p>
      </div>
    )
  }

  if (err && !detail) {
    return (
      <div className="px-5 py-10 sm:px-8">
        <p className="text-sm text-red-600 dark:text-red-400">{err}</p>
        <Link
          to="/user/forms"
          className="mt-4 inline-block text-sm font-medium text-violet-600 hover:underline dark:text-violet-400"
        >
          Back to list
        </Link>
      </div>
    )
  }

  const fields = detail.fields_schema || []
  if (fields.length === 0) {
    return (
      <div className="px-5 py-10 sm:px-8">
        <p className="text-zinc-700 dark:text-zinc-300">This template has no detected fields yet.</p>
        <Link
          to="/user/forms"
          className="mt-4 inline-block text-sm font-medium text-violet-600 hover:underline dark:text-violet-400"
        >
          Back
        </Link>
      </div>
    )
  }

  return (
    <div className="px-5 py-8 sm:px-8">
      <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
        {detail.title}
      </h1>
      <p className="mt-1 text-sm text-zinc-500">{detail.original_filename}</p>
      <form
        className="mt-8 flex flex-col gap-4 rounded-xl border border-zinc-200 bg-zinc-50/50 p-5 dark:border-zinc-700 dark:bg-zinc-800/40"
        onSubmit={onSubmit}
      >
        {fields.map((f) => (
          <label key={f.key} className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
            {f.label}
            <input
              value={answers[f.key] ?? ''}
              onChange={(e) => setField(f.key, e.target.value)}
              placeholder={f.placeholders?.[0] || f.key}
              required
              className={inputClass}
            />
          </label>
        ))}
        {err && <p className="text-sm text-red-600 dark:text-red-400">{err}</p>}
        <div className="flex flex-wrap gap-2">
          <button
            type="submit"
            disabled={busy}
            className="rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-violet-700 disabled:opacity-60"
          >
            {busy ? 'Submitting…' : 'Submit & generate filled form'}
          </button>
          <Link
            to="/user/forms"
            className="inline-flex items-center rounded-lg border border-zinc-300 px-4 py-2.5 text-sm font-medium text-zinc-800 transition hover:bg-zinc-100 dark:border-zinc-600 dark:text-zinc-200 dark:hover:bg-zinc-800"
          >
            Cancel
          </Link>
        </div>
      </form>
    </div>
  )
}
