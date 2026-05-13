import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, downloadSubmissionFile } from '../api'
import DocumentPreview from '../components/DocumentPreview.jsx'
import { toastError, toastSuccess } from '../toast.js'
import {
  btnMutedClass,
  btnPrimaryClass,
  btnSecondaryClass,
  GlassCard,
  userAreaInputClass,
} from '../components/UserAreaLayout.jsx'

function formatWhen(iso) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
  } catch {
    return String(iso)
  }
}

function normalizeAnswers(raw) {
  const out = {}
  if (!raw || typeof raw !== 'object') return out
  for (const [k, v] of Object.entries(raw)) {
    out[String(k)] = v == null ? '' : String(v)
  }
  return out
}

/** Build ordered rows: every template field first, then any answer keys not in the template. */
function buildFormRows(fieldsSchema, answers) {
  const schema = Array.isArray(fieldsSchema) ? fieldsSchema : []
  const ans = normalizeAnswers(answers)
  const seen = new Set()
  const rows = []

  schema.forEach((f, idx) => {
    const fieldKey = f && typeof f.key === 'string' ? f.key : null
    if (!fieldKey) return
    seen.add(fieldKey)
    rows.push({
      reactKey: `schema-${idx}-${fieldKey}`,
      fieldKey,
      label: (f.label && String(f.label).trim()) || fieldKey,
      placeholders: Array.isArray(f.placeholders) ? f.placeholders : [],
      input_type: (f.input_type && String(f.input_type).trim()) || 'text',
      value: ans[fieldKey] ?? '',
    })
  })

  const extraKeys = Object.keys(ans)
    .filter((k) => !seen.has(k))
    .sort((a, b) => a.localeCompare(b))
  for (const k of extraKeys) {
    rows.push({
      reactKey: `extra-${k}`,
      fieldKey: k,
      label: k,
      placeholders: [],
      input_type: 'text',
      value: ans[k] ?? '',
    })
  }

  return rows
}

export default function AdminSubmissionDetail() {
  const { submissionId } = useParams()
  const nav = useNavigate()
  const [detail, setDetail] = useState(null)
  const [loadFailed, setLoadFailed] = useState(false)
  const [previewRev, setPreviewRev] = useState(0)

  useEffect(() => {
    ; (async () => {
      try {
        setLoadFailed(false)
        const d = await api(`/forms/admin/submissions/${submissionId}`)
        setDetail(d)
      } catch (e) {
        setLoadFailed(true)
        toastError(e.message)
        setDetail(null)
      }
    })()
  }, [submissionId])

  const formRows = useMemo(() => {
    if (!detail) return []
    return buildFormRows(detail.fields_schema, detail.answers)
  }, [detail])

  if (!detail && !loadFailed) {
    return (
      <div className="py-12 text-center text-sm text-slate-600">Loading…</div>
    )
  }

  if (loadFailed && !detail) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-slate-700">This submission could not be loaded.</p>
        <Link to="/admin/submissions" className={`inline-flex ${btnSecondaryClass}`}>
          ← All submissions
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-3 border-b border-slate-200/80 pb-6 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-600">Submission</p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">{detail.template_title}</h1>
          <p className="mt-2 text-sm text-slate-600">
            <span className="font-medium text-slate-800">{detail.user_email}</span>
            {detail.user_name ? <span className="text-slate-500"> · {detail.user_name}</span> : null}
            <span className="block pt-1 text-xs text-slate-500">{formatWhen(detail.created_at)}</span>
          </p>
          <p className="mt-1 text-xs text-slate-500">Template file: {detail.template_original_filename}</p>
        </div>
      </div>
      {detail.has_filled_file && detail.filled_filename ? (
        <GlassCard className="max-w-none overflow-hidden p-0 sm:p-0">
          <div className="flex flex-col gap-3 border-b border-slate-200/80 px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-600">Filled document</p>
              <h2 className="mt-1 text-lg font-bold text-slate-900">Full merged preview</h2>
              <p className="mt-0.5 truncate text-xs text-slate-500" title={detail.filled_filename}>
                {detail.filled_filename}
              </p>
            </div>
            <button
              type="button"
              onClick={() => setPreviewRev((r) => r + 1)}
              className="shrink-0 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm hover:border-indigo-200 hover:text-indigo-800 sm:text-sm"
            >
              Reload preview
            </button>
          </div>
          <div className="bg-slate-50/50 px-2 py-3 sm:px-4 sm:py-4">
            <DocumentPreview
              submissionId={detail.id}
              filename={detail.filled_filename}
              revision={previewRev}
              onlyOfficeAdmin={true}
            />
          </div>
        </GlassCard>
      ) : null}




    </div>
  )
}
