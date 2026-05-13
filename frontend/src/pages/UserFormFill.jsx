import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, getToken } from '../api'
import DocumentPreview from '../components/DocumentPreview.jsx'
import { toastError, toastSuccess } from '../toast.js'
import {
  btnPrimaryClass,
  btnSecondaryClass,
  GlassCard,
  UserAreaLayout,
  userAreaInputClass,
} from '../components/UserAreaLayout.jsx'

export default function UserFormFill() {
  const { id } = useParams()
  const nav = useNavigate()
  const [detail, setDetail] = useState(null)
  const [answers, setAnswers] = useState({})
  const [loadFailed, setLoadFailed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [previewRev, setPreviewRev] = useState(0)

  useEffect(() => {
    if (!getToken()) {
      nav('/user/login')
      return
    }
    ;(async () => {
      try {
        setLoadFailed(false)
        const d = await api(`/forms/templates/${id}`)
        setDetail(d)
        const init = {}
        for (const f of d.fields_schema || []) {
          init[f.key] = ''
        }
        setAnswers(init)
      } catch (e) {
        setLoadFailed(true)
        toastError(e.message)
      }
    })()
  }, [id, nav])

  function setField(key, v) {
    setAnswers((a) => ({ ...a, [key]: v }))
  }

  async function onSubmit(e) {
    e.preventDefault()
    setBusy(true)
    try {
      const res = await api(`/forms/templates/${id}/submit`, {
        method: 'POST',
        body: { answers },
      })
      toastSuccess('Submitted. Your merged file is ready in My submissions.')
      nav(`/user/submissions?highlight=${res.submission_id}`)
    } catch (ex) {
      toastError(ex.message)
    } finally {
      setBusy(false)
    }
  }

  if (!detail && !loadFailed) {
    return (
      <UserAreaLayout wide centerContent>
        <GlassCard>
          <p className="text-center text-sm text-slate-600">Loading…</p>
        </GlassCard>
      </UserAreaLayout>
    )
  }

  if (loadFailed && !detail) {
    return (
      <UserAreaLayout wide centerContent={false}>
        <GlassCard>
          <p className="text-sm text-slate-700">This form could not be loaded.</p>
          <Link
            to="/user/forms"
            className="mt-5 inline-flex font-semibold text-indigo-600 hover:text-indigo-500"
          >
            ← Back to forms
          </Link>
        </GlassCard>
      </UserAreaLayout>
    )
  }

  const fields = detail.fields_schema || []
  if (fields.length === 0) {
    return (
      <UserAreaLayout wide centerContent={false}>
        <GlassCard>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-600">Form</p>
          <h1 className="mt-1 text-xl font-bold text-slate-900">{detail.title}</h1>
          <p className="mt-4 text-sm text-slate-700">
            This form has no fields to fill yet. Please contact your administrator.
          </p>
          <Link
            to="/user/forms"
            className="mt-6 inline-flex font-semibold text-indigo-600 hover:text-indigo-500"
          >
            ← Back to forms
          </Link>
        </GlassCard>
      </UserAreaLayout>
    )
  }

  return (
    <UserAreaLayout wide centerContent={false}>
      <GlassCard className="max-w-xl">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-600">Form</p>
        <h1 className="mt-1 text-xl font-bold text-slate-900">{detail.title}</h1>
        <p className="mt-1 text-sm text-slate-500">Fill the fields below for this form only.</p>

        <form className="mt-6 flex flex-col gap-5" onSubmit={onSubmit}>
          {fields.map((f) => (
            <label key={f.key} className="text-sm font-medium text-slate-800">
              {f.label}
              <input
                value={answers[f.key] ?? ''}
                onChange={(e) => setField(f.key, e.target.value)}
                placeholder={f.placeholders?.[0] || f.key}
                required
                className={userAreaInputClass}
              />
            </label>
          ))}
          <div className="flex flex-wrap gap-3 pt-1">
            <button type="submit" disabled={busy} className={btnPrimaryClass}>
              {busy ? 'Submitting…' : 'Submit'}
            </button>
            <Link to="/user/forms" className={btnSecondaryClass}>
              Cancel
            </Link>
          </div>
        </form>
      </GlassCard>

      {detail && (
        <GlassCard className="mt-6 overflow-hidden p-0">
          <button
            type="button"
            onClick={() => {
              setPreviewOpen((o) => {
                if (!o) setPreviewRev((r) => r + 1)
                return !o
              })
            }}
            className="flex w-full items-center justify-between px-6 py-4 text-left text-sm font-semibold text-slate-800 transition hover:bg-slate-50/80"
          >
            <span>Template preview</span>
            <span className="text-xs font-medium text-indigo-600">{previewOpen ? 'Hide' : 'Show'}</span>
          </button>
          {previewOpen && (
            <div className="border-t border-slate-200/80 bg-slate-50/40 px-4 py-4 sm:px-6 sm:py-5">
              <div className="mb-3 flex justify-end">
                <button
                  type="button"
                  onClick={() => setPreviewRev((r) => r + 1)}
                  className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm hover:border-indigo-200 hover:text-indigo-800"
                >
                  Reload
                </button>
              </div>
              <DocumentPreview
                templateId={Number(id)}
                filename={detail.original_filename}
                revision={previewRev}
                onlyOfficeAdmin={false}
              />
            </div>
          )}
        </GlassCard>
      )}

      <p className="mt-8 text-center text-sm text-slate-500 sm:text-left">
        <Link to="/user/forms" className="font-medium text-indigo-600 hover:text-indigo-500 hover:underline">
          ← All forms
        </Link>
      </p>
    </UserAreaLayout>
  )
}
