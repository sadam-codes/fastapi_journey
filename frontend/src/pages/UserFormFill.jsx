import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
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

const W = 400
const H = 160

function SignaturePad({ value, onChange, disabled }) {
  const canvasRef = useRef(null)
  const drawing = useRef(false)
  const stroked = useRef(false)
  const inited = useRef(false)

  const setupCanvas = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const dpr = window.devicePixelRatio || 1
    canvas.width = W * dpr
    canvas.height = H * dpr
    canvas.style.width = `${W}px`
    canvas.style.height = `${H}px`
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, W, H)
    ctx.strokeStyle = '#0f172a'
    ctx.lineWidth = 2
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
  }, [])

  useEffect(() => {
    if (inited.current) return
    setupCanvas()
    inited.current = true
  }, [setupCanvas])

  const pos = useCallback((e) => {
    const canvas = canvasRef.current
    if (!canvas) return { x: 0, y: 0 }
    const rect = canvas.getBoundingClientRect()
    const clientX = e.clientX ?? (e.touches && e.touches[0]?.clientX) ?? 0
    const clientY = e.clientY ?? (e.touches && e.touches[0]?.clientY) ?? 0
    return { x: clientX - rect.left, y: clientY - rect.top }
  }, [])

  const exportPng = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    try {
      onChange(canvas.toDataURL('image/png'))
    } catch {
      toastError('Could not read signature from canvas.')
    }
  }, [onChange])

  const clear = useCallback(() => {
    stroked.current = false
    setupCanvas()
    onChange('')
  }, [onChange, setupCanvas])

  useEffect(() => {
    if (!value && inited.current) {
      setupCanvas()
    }
  }, [value, setupCanvas])

  function onPointerDown(e) {
    if (disabled) return
    const canvas = canvasRef.current
    if (!canvas) return
    e.preventDefault()
    drawing.current = true
    stroked.current = false
    try {
      canvas.setPointerCapture(e.pointerId)
    } catch {
      /* ignore */
    }
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const { x, y } = pos(e)
    ctx.beginPath()
    ctx.moveTo(x, y)
  }

  function onPointerMove(e) {
    if (!drawing.current || disabled) return
    e.preventDefault()
    stroked.current = true
    const canvas = canvasRef.current
    const ctx = canvas?.getContext('2d')
    if (!ctx) return
    const { x, y } = pos(e)
    ctx.lineTo(x, y)
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(x, y)
  }

  function onPointerUp(e) {
    if (!drawing.current) return
    drawing.current = false
    try {
      canvasRef.current?.releasePointerCapture(e.pointerId)
    } catch {
      /* ignore */
    }
    if (stroked.current) {
      exportPng()
    }
  }

  return (
    <div className="mt-1.5 space-y-2">
      <canvas
        ref={canvasRef}
        className="touch-none rounded-lg border border-slate-300 bg-white shadow-inner"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={onPointerUp}
      />
      <div className="flex flex-wrap gap-2">
        <button type="button" className={btnSecondaryClass} disabled={disabled} onClick={clear}>
          Clear
        </button>
        {value ? (
          <span className="self-center text-xs font-medium text-emerald-700">Signature captured</span>
        ) : (
          <span className="self-center text-xs text-slate-500">Draw above, then release to save</span>
        )}
      </div>
    </div>
  )
}

function inputTypeOf(f) {
  const t = (f.input_type || 'text').toLowerCase()
  return t
}

/** Buckets fields so checkboxes and radios are not merged into one row under the same doc section title. */
function clusterBucket(f) {
  const it = inputTypeOf(f)
  if (it === 'checkbox') return 'checkbox'
  if (it === 'radio') return 'radio'
  if (it === 'signature') return 'signature'
  return 'other'
}

function clusterMergeKey(f) {
  const gl = f.group_label != null && String(f.group_label).trim() ? String(f.group_label).trim() : ''
  const g = gl || '__none__'
  const b = clusterBucket(f)
  if (b === 'radio') {
    const rg = (f.radio_group && String(f.radio_group).trim()) || f.key
    return `${g}|radio|${rg}`
  }
  return `${g}|${b}`
}

function renderFieldControl(f, answers, setField, disabled) {
  const it = inputTypeOf(f)
  const v = answers[f.key] ?? ''

  if (it === 'textarea') {
    return (
      <textarea
        value={v}
        onChange={(e) => setField(f.key, e.target.value)}
        placeholder={f.placeholders?.[0] || f.key}
        required
        rows={4}
        disabled={disabled}
        className={userAreaInputClass}
      />
    )
  }

  if (it === 'checkbox') {
    return (
      <label className="mt-1.5 flex cursor-pointer items-center gap-2 text-sm font-normal text-slate-700">
        <input
          type="checkbox"
          checked={v === 'true'}
          onChange={(e) => setField(f.key, e.target.checked ? 'true' : '')}
          required={f.required === true}
          disabled={disabled}
          className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
        />
        {f.checkbox_hint ? <span className="text-slate-600">{f.checkbox_hint}</span> : null}
      </label>
    )
  }

  if (it === 'radio') {
    const rg = (f.radio_group && String(f.radio_group).trim()) || f.key
    const optVal = (f.radio_option != null && String(f.radio_option).trim()) || f.key
    const cur = answers[rg] ?? ''
    return (
      <label className="mt-1.5 flex cursor-pointer items-center gap-2 text-sm font-normal text-slate-700">
        <input
          type="radio"
          name={rg}
          value={optVal}
          checked={cur === optVal}
          onChange={() => setField(rg, optVal)}
          required={f.required === true}
          disabled={disabled}
          className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
        />
        {f.checkbox_hint ? <span className="text-slate-600">{f.checkbox_hint}</span> : null}
      </label>
    )
  }

  if (it === 'signature') {
    return <SignaturePad value={v} onChange={(dataUrl) => setField(f.key, dataUrl)} disabled={disabled} />
  }

  const common = {
    value: v,
    onChange: (e) => setField(f.key, e.target.value),
    placeholder: f.placeholders?.[0] || f.key,
    required: true,
    disabled,
    className: userAreaInputClass,
  }

  if (it === 'number') {
    return <input type="number" step="any" {...common} />
  }
  if (it === 'email') {
    return <input type="email" autoComplete="email" {...common} />
  }
  if (it === 'tel') {
    return <input type="tel" autoComplete="tel" {...common} />
  }
  if (it === 'date') {
    return <input type="date" {...common} />
  }

  return <input type="text" {...common} />
}

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
        const radioInited = new Set()
        for (const f of d.fields_schema || []) {
          const it = (f.input_type || 'text').toLowerCase()
          if (it === 'radio' && f.radio_group) {
            const rg = String(f.radio_group).trim()
            if (rg && !radioInited.has(rg)) {
              radioInited.add(rg)
              init[rg] = ''
            }
          } else {
            init[f.key] = ''
          }
        }
        setAnswers(init)
      } catch (e) {
        setLoadFailed(true)
        toastError(e.message)
      }
    })()
  }, [id, nav])

  const fieldClusters = useMemo(() => {
    const list = detail?.fields_schema || []
    const raw = []
    for (const f of list) {
      const g =
        f.group_label != null && String(f.group_label).trim() ? String(f.group_label).trim() : null
      const mk = clusterMergeKey(f)
      const prev = raw[raw.length - 1]
      if (prev && prev.kind === 'fields' && prev.mergeKey === mk) {
        prev.fields.push(f)
      } else {
        raw.push({ kind: 'fields', mergeKey: mk, groupHeading: g, fields: [f] })
      }
    }
    return raw.map((c, i) => ({
      kind: c.kind,
      groupHeading: c.groupHeading,
      fields: c.fields,
      suppressHeading:
        i > 0 && Boolean(c.groupHeading) && c.groupHeading === raw[i - 1].groupHeading,
    }))
  }, [detail])

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
      <GlassCard className="max-w-3xl">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-600">Form</p>
        <h1 className="mt-1 text-xl font-bold text-slate-900">{detail.title}</h1>
        <p className="mt-1 text-sm text-slate-500">Fill the fields below for this form only.</p>

        <form className="mt-6 flex flex-col gap-7" onSubmit={onSubmit}>
          {fieldClusters.map((cluster, ci) => {
            const rowLayout = cluster.groupHeading && cluster.fields.length > 1
            return (
              <div
                key={`cluster-${ci}`}
                className={`text-sm text-slate-800 ${cluster.suppressHeading ? 'mt-5 border-t border-slate-100 pt-4' : ''}`}
              >
                {cluster.groupHeading && !cluster.suppressHeading ? (
                  <p className="mb-2 border-b border-slate-200 pb-1.5 text-sm font-semibold leading-snug text-slate-900">
                    {cluster.groupHeading}
                  </p>
                ) : null}
                {rowLayout ? (
                  <div className="grid grid-cols-2 items-end gap-x-5 gap-y-4 font-medium sm:grid-cols-4">
                    {cluster.fields.map((f) => (
                      <div key={f.key} className="min-w-0">
                        <span className="block text-xs font-medium text-slate-700">{f.label}</span>
                        {inputTypeOf(f) === 'signature' ? (
                          <p className="mt-0.5 text-xs font-normal text-slate-500">
                            Sign with mouse or touch
                          </p>
                        ) : null}
                        <div className="mt-1.5 font-normal">{renderFieldControl(f, answers, setField, busy)}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  cluster.fields.map((f) => (
                    <div key={f.key} className="font-medium">
                      <span>{f.label}</span>
                      {inputTypeOf(f) === 'signature' ? (
                        <p className="mt-0.5 text-xs font-normal text-slate-500">Sign with mouse or touch</p>
                      ) : null}
                      <div className="mt-1.5 font-normal">{renderFieldControl(f, answers, setField, busy)}</div>
                    </div>
                  ))
                )}
              </div>
            )
          })}
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
