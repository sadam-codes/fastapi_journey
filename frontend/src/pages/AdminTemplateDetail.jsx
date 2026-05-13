import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, NavLink, Outlet, useNavigate, useOutletContext, useParams } from 'react-router-dom'
import { api, downloadAdminTemplate, patchAdminTemplateFieldTypes, updateAdminTemplate } from '../api'
import { useConfirm } from '../components/ConfirmProvider.jsx'
import { toastError, toastInfo, toastSuccess, toastWarning } from '../toast.js'
import DocumentPreview from '../components/DocumentPreview.jsx'
import OnlyOfficeDocx from '../components/OnlyOfficeDocx.jsx'
import {
  btnPrimaryClass,
  btnSecondaryClass,
  fileInputClass,
  userAreaInputClass,
} from '../components/UserAreaLayout.jsx'

function SvgOutline({ className, children }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
      className={className}
      aria-hidden
    >
      {children}
    </svg>
  )
}

function IconDownload({ className }) {
  return (
    <SvgOutline className={className}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3"
      />
    </SvgOutline>
  )
}

function IconSpinner({ className }) {
  return (
    <SvgOutline className={className}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99"
      />
    </SvgOutline>
  )
}

function IconTrash({ className }) {
  return (
    <SvgOutline className={className}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
      />
    </SvgOutline>
  )
}

function isDocxFilename(name) {
  return typeof name === 'string' && name.toLowerCase().endsWith('.docx')
}

const FIELD_TYPE_OPTIONS = [
  { value: 'text', label: 'Text (single line)' },
  { value: 'textarea', label: 'Text (multiple lines)' },
  { value: 'number', label: 'Number' },
  { value: 'email', label: 'Email' },
  { value: 'tel', label: 'Phone' },
  { value: 'date', label: 'Date' },
  { value: 'checkbox', label: 'Checkbox' },
  { value: 'radio', label: 'Radio' },
  { value: 'signature', label: 'Signature' },
]

/** Shared HTML `name` for radios: form section from the doc (`group_label`), else the field key. */
function inferredRadioGroup(row) {
  const gl = row.group_label != null ? String(row.group_label).trim() : ''
  if (gl) return gl.slice(0, 128)
  return String(row.key || '').trim().slice(0, 128)
}

export function AdminTemplateFieldsTab() {
  const { template, detail, reload } = useOutletContext()
  const confirm = useConfirm()
  const [rows, setRows] = useState([])
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const fs = detail?.fields_schema
    if (!Array.isArray(fs)) {
      setRows([])
      return
    }
    setRows(fs.map((f) => ({ ...f, input_type: f.input_type || 'text' })))
  }, [detail])

  async function onSave() {
    if (!template) return
    setBusy(true)
    try {
      const fields = rows.map((r) => {
        const it = (r.input_type || 'text').toLowerCase()
        const base = { key: r.key, input_type: it }
        if (it === 'radio') {
          base.radio_group = inferredRadioGroup(r)
          base.radio_option = String(r.key || '').trim().slice(0, 256)
        }
        return base
      })
      await patchAdminTemplateFieldTypes(template.id, { fields })
      toastSuccess('Field types saved.')
      await reload()
    } catch (ex) {
      toastError(ex.message)
    } finally {
      setBusy(false)
    }
  }

  /** Flow: {{a}}{{b}}… in doc → upload → rows here → all Checkbox → user ticks → merge ☑/☐. */
  async function onSaveAllCheckboxes() {
    if (!template || !rows.length) return
    const ok = await confirm({
      title: 'Save every field as Checkbox?',
      message:
        'Each row will be saved as Checkbox (filled file: ☑ if ticked, ☐ if not). Signature fields are left as Signature. Other types (text, date, …) become Checkbox — use only on checkbox-style templates.',
      confirmLabel: 'Save all as Checkbox',
      cancelLabel: 'Cancel',
      variant: 'default',
    })
    if (!ok) return
    setBusy(true)
    try {
      const fields = rows.map((r) => {
        const it = (r.input_type || 'text').toLowerCase()
        if (it === 'signature') return { key: r.key, input_type: 'signature' }
        if (it === 'radio') {
          return {
            key: r.key,
            input_type: 'radio',
            radio_group: inferredRadioGroup(r),
            radio_option: String(r.key || '').trim().slice(0, 256),
          }
        }
        return { key: r.key, input_type: 'checkbox' }
      })
      await patchAdminTemplateFieldTypes(template.id, { fields })
      toastSuccess('All applicable fields saved as Checkbox.')
      await reload()
    } catch (ex) {
      toastError(ex.message)
    } finally {
      setBusy(false)
    }
  }

  if (!detail) {
    return <p className="p-4 text-sm text-slate-500">Loading…</p>
  }

  if (!rows.length) {
    return (
      <div className="mx-auto max-w-xl space-y-4 px-4 py-8">
        <p className="text-sm font-semibold text-slate-800">Generated fields</p>
        <p className="text-sm text-slate-600">
          No <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">{'{{field_name}}'}</code> placeholders were
          detected in the saved template yet. Save your document in the <span className="font-medium">Edit</span> tab
          (or re-upload), then open this tab again.
        </p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl space-y-5 px-4 py-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Generated fields</p>
        <p className="mt-1 text-sm text-slate-600">
          One <span className="font-mono text-xs">{'{{placeholder}}'}</span> per field. Pick type per row, or use the
          button below for an all-checkbox template (<span className="font-serif">☑</span> /{' '}
          <span className="font-serif">☐</span> in the merged file).{' '}
          <span className="font-medium text-slate-700">Radio:</span> rows that share the same form section (see each
          card) are one mutually exclusive group; each placeholder is one option (value = that field's key).
        </p>
        <p className="mt-2 font-mono text-[11px] leading-relaxed text-slate-500">
          doc → upload → detect rows → checkbox types → user form → merge
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {rows.map((r, i) => (
          <div
            key={r.key}
            className="flex flex-col rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
          >
            <p className="text-sm font-semibold text-slate-900">{r.label || r.key}</p>
            <p className="mt-0.5 font-mono text-xs text-slate-500">{r.key}</p>
            {r.group_label ? (
              <p className="mt-1 text-[11px] font-medium text-slate-600">Form section: {r.group_label}</p>
            ) : null}
            {r.placeholders?.length ? (
              <p className="mt-1 truncate font-mono text-[11px] text-slate-500" title={r.placeholders.join(' · ')}>
                {r.placeholders.join(' · ')}
              </p>
            ) : null}
            <label className="mt-3 block text-xs font-medium text-slate-600">
              Type
              <select
                value={r.input_type || 'text'}
                onChange={(e) => {
                  const v = e.target.value
                  setRows((prev) => prev.map((x, j) => (j === i ? { ...x, input_type: v } : x)))
                }}
                className={`${userAreaInputClass} mt-1 !text-sm`}
              >
                {FIELD_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-3">
        <button type="button" disabled={busy} className={btnPrimaryClass} onClick={() => void onSave()}>
          {busy ? 'Saving…' : 'Save field types'}
        </button>
        <button type="button" disabled={busy} className={btnSecondaryClass} onClick={() => void onSaveAllCheckboxes()}>
          Save all as Checkbox
        </button>
      </div>
    </div>
  )
}

function subTabClass({ isActive }) {
  return `rounded-lg px-3 py-1.5 text-xs font-semibold transition sm:px-4 sm:py-2 sm:text-sm ${
    isActive
      ? 'bg-indigo-600 text-white shadow-sm'
      : 'text-slate-600 hover:bg-slate-100'
  }`
}

export function AdminTemplatePreviewTab() {
  const { template, previewRev, bumpPreview } = useOutletContext()
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-slate-200 bg-white px-3 py-2 sm:px-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Preview</p>
          <p className="mt-0.5 max-w-xl text-[11px] leading-snug text-slate-500 sm:text-xs">
            Read-only here. Open the <span className="font-semibold text-slate-700">Edit</span> tab to type in the
            document.
          </p>
        </div>
        <button type="button" onClick={() => bumpPreview()} className={`${btnSecondaryClass} !py-2 text-xs`}>
          Reload
        </button>
      </div>
      <div className="flex min-h-[calc(100svh-10.5rem)] flex-1 flex-col bg-slate-200/40">
        <DocumentPreview
          templateId={template.id}
          filename={template.original_filename}
          revision={previewRev}
          onlyOfficeAdmin
          fillHeight
        />
      </div>
    </div>
  )
}

export function AdminTemplateEditTab() {
  const ctx = useOutletContext()
  const {
    template,
    editTitle,
    setEditTitle,
    editFile,
    setEditFile,
    editBusy,
    editOoKey,
    onSaveMetadata,
    onSaveDocx,
    saveDocxBusy,
  } = ctx
  const docx = isDocxFilename(template.original_filename)

  if (docx) {
    return (
      <div className="flex min-h-0 flex-1 flex-col">
        <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-slate-200 bg-white px-3 py-2 sm:px-4">
          <p className="text-xs text-slate-600">
            Wait for <span className="font-semibold">Opening document…</span> to finish, then click in the page and
            type. Click <span className="font-semibold">Save</span> to store your edits, then open the{' '}
            <span className="font-semibold">Preview</span> tab and use <span className="font-semibold">Reload</span> if
            needed.
          </p>
          <button
            type="button"
            disabled={saveDocxBusy}
            className={btnPrimaryClass}
            onClick={() => onSaveDocx()}
          >
            {saveDocxBusy ? 'Saving…' : 'Save'}
          </button>
        </div>
        <div className="flex min-h-[calc(100svh-10.5rem)] flex-1 flex-col bg-slate-900/5">
          <OnlyOfficeDocx
            templateId={template.id}
            mode="edit"
            admin
            revision={editOoKey}
            className="min-h-0 flex-1 rounded-none border-0 shadow-none"
          />
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-xl space-y-5 px-4 py-6">
      <p className="text-sm text-amber-950">
        OnlyOffice is for .docx files. Update the display title or replace the file, or download to edit elsewhere.
      </p>
      <label className="block text-sm font-medium text-slate-800">
        Display title
        <input
          value={editTitle}
          onChange={(e) => setEditTitle(e.target.value)}
          className={`${userAreaInputClass} mt-1.5`}
        />
      </label>
      <details className="rounded-xl border border-slate-200/80 bg-slate-50/50 p-4">
        <summary className="cursor-pointer text-sm font-semibold text-slate-800">Replace file</summary>
        <input
          type="file"
          accept=".pdf,.docx,.png,.jpg,.jpeg,.webp,.gif,.tiff,.bmp"
          onChange={(e) => setEditFile(e.target.files?.[0] || null)}
          className={`${fileInputClass} mt-3`}
        />
      </details>
      <div className="flex flex-wrap gap-3">
        <button type="button" disabled={editBusy} className={btnPrimaryClass} onClick={() => onSaveMetadata()}>
          {editBusy ? 'Saving…' : 'Save changes'}
        </button>
      </div>
    </div>
  )
}

export default function AdminTemplateDetail() {
  const { templateId } = useParams()
  const navigate = useNavigate()
  const confirm = useConfirm()
  const [template, setTemplate] = useState(null)
  const [detail, setDetail] = useState(null)
  const [notFound, setNotFound] = useState(false)
  const [ooStatus, setOoStatus] = useState(null)
  const [previewRev, setPreviewRev] = useState(0)
  const [editOoKey, setEditOoKey] = useState(0)
  const [editTitle, setEditTitle] = useState('')
  const [editFile, setEditFile] = useState(null)
  const [editBusy, setEditBusy] = useState(false)
  const [deletingId, setDeletingId] = useState(false)
  const [dlBusy, setDlBusy] = useState(false)

  const [saveDocxBusy, setSaveDocxBusy] = useState(false)

  const bumpPreview = useCallback(() => {
    setPreviewRev((r) => r + 1)
  }, [])

  const reload = useCallback(async () => {
    const id = Number(templateId)
    if (!Number.isFinite(id)) {
      setNotFound(true)
      setTemplate(null)
      setDetail(null)
      return
    }
    try {
      const rows = await api('/forms/admin/templates')
      const t = rows.find((x) => x.id === id)
      if (!t) {
        setNotFound(true)
        setTemplate(null)
        setDetail(null)
        return
      }
      setNotFound(false)
      setTemplate(t)
      const d = await api(`/forms/admin/templates/${t.id}`)
      setDetail(d)
    } catch {
      setNotFound(true)
      setTemplate(null)
      setDetail(null)
    }
  }, [templateId])

  useEffect(() => {
    setNotFound(false)
    setTemplate(null)
    setDetail(null)
    setPreviewRev(0)
    setEditOoKey(0)
    setEditFile(null)
  }, [templateId])

  useEffect(() => {
    void reload()
  }, [reload])

  useEffect(() => {
    ;(async () => {
      try {
        const s = await api('/forms/admin/onlyoffice/status')
        setOoStatus(s)
      } catch {
        setOoStatus({ enabled: false })
      }
    })()
  }, [])

  useEffect(() => {
    if (!ooStatus?.hint) return
    toastInfo(ooStatus.hint, { toastId: 'onlyoffice-admin-hint', autoClose: 10000 })
  }, [ooStatus?.hint])

  useEffect(() => {
    if (detail) {
      setEditTitle(detail.title ?? template?.title ?? '')
    }
  }, [detail, template?.title])

  async function onDownload() {
    if (!template) return
    setDlBusy(true)
    try {
      await downloadAdminTemplate(template.id, template.original_filename)
    } catch (ex) {
      toastError(ex.message)
    } finally {
      setDlBusy(false)
    }
  }

  async function onDelete() {
    if (!template) return
    const ok = await confirm({
      title: 'Delete template?',
      message:
        'Delete this template? All user submissions for it will be removed. This cannot be undone.',
      confirmLabel: 'Delete',
      cancelLabel: 'Cancel',
      variant: 'danger',
    })
    if (!ok) return
    setDeletingId(true)
    try {
      await api(`/forms/admin/templates/${template.id}`, { method: 'DELETE' })
      navigate('/admin/templates', { replace: true })
    } catch (ex) {
      toastError(ex.message)
    } finally {
      setDeletingId(false)
    }
  }

  async function onSaveMetadata() {
    if (!template || !detail) return
    const currentTitle = (detail.title ?? template.title ?? '').trim()
    const titleChanged = editTitle.trim() !== currentTitle

    if (!editFile && !titleChanged) {
      toastWarning('Change the display title or choose a replacement file.')
      return
    }

    const replacedFile = Boolean(editFile)
    setEditBusy(true)
    try {
      const data2 = await updateAdminTemplate(template.id, {
        title: editTitle,
        file: editFile || undefined,
      })
      toastSuccess(data2.message || 'Saved.')
      setDetail({
        id: data2.id,
        title: data2.title,
        original_filename: data2.original_filename,
        fields_schema: data2.fields_schema || [],
        created_at: detail.created_at,
      })
      setEditFile(null)
      bumpPreview()
      if (replacedFile) {
        setEditOoKey((k) => k + 1)
      }
      await reload()
    } catch (ex) {
      toastError(ex.message)
    } finally {
      setEditBusy(false)
    }
  }

  const onSaveDocx = useCallback(async () => {
    if (!template) return
    setSaveDocxBusy(true)
    try {
      const r = await api(`/forms/admin/templates/${template.id}/onlyoffice/forcesave`, { method: 'POST' })
      if (r.timed_out) {
        toastWarning(r.message || 'Save status unclear; check Preview after a few seconds.')
      } else {
        toastSuccess(r.message || 'Saved.')
      }
      bumpPreview()
      setEditOoKey((k) => k + 1)
      window.setTimeout(() => {
        void reload()
      }, 900)
    } catch (ex) {
      toastError(ex.message)
    } finally {
      setSaveDocxBusy(false)
    }
  }, [template, bumpPreview, reload])

  const outletContext = useMemo(
    () => ({
      template,
      detail,
      previewRev,
      bumpPreview,
      editTitle,
      setEditTitle,
      editFile,
      setEditFile,
      editBusy,
      editOoKey,
      onSaveMetadata,
      onSaveDocx,
      saveDocxBusy,
      reload,
    }),
    [
      template,
      detail,
      previewRev,
      bumpPreview,
      editTitle,
      editFile,
      editBusy,
      editOoKey,
      onSaveMetadata,
      onSaveDocx,
      saveDocxBusy,
      reload,
    ],
  )

  if (notFound) {
    return (
      <div className="py-12 text-center">
        <p className="text-lg font-semibold text-slate-900">Template not found</p>
        <p className="mt-2 text-sm text-slate-600">It may have been deleted or the link is invalid.</p>
        <Link to="/admin/templates" className={`mt-8 inline-flex ${btnSecondaryClass}`}>
          Back to templates
        </Link>
      </div>
    )
  }

  if (!template) {
    return (
      <div className="py-16 text-center">
        <p className="text-sm text-slate-500">Loading template…</p>
      </div>
    )
  }

  const docx = isDocxFilename(template.original_filename)

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="shrink-0 border-b border-slate-200 bg-white">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 px-3 py-2.5 sm:px-4">
          <nav className="text-xs text-slate-500 sm:text-sm">
            <Link to="/admin/templates" className="font-medium text-indigo-600 hover:text-indigo-500 hover:underline">
              Templates
            </Link>
            <span className="mx-1.5 text-slate-300">/</span>
            <span className="font-medium text-slate-800">{template.title}</span>
          </nav>
          <span className="hidden h-4 w-px bg-slate-200 sm:block" aria-hidden />
          <h1 className="min-w-0 max-w-[min(100%,28rem)] truncate text-sm font-bold text-slate-900 sm:text-base">
            {template.original_filename}
          </h1>
          <div className="flex flex-wrap items-center gap-1.5 sm:ml-auto">
            <span
              className="rounded-md bg-indigo-50 px-2 py-0.5 text-[10px] font-semibold text-indigo-800 sm:text-xs"
              title={
                'Placeholders like {{field_name}} are counted from the last copy saved on the server ' +
                '(after Save in Edit, or re-upload). Unsaved editor changes are not included yet. ' +
                'If the count stays wrong after Save, OnlyOffice must be able to reach your app ' +
                '(PUBLIC_APP_URL / callback URL).'
              }
            >
              {(detail?.fields_schema?.length ?? template.field_count) ?? 0} fields
            </span>
            {docx && (
              <span className="rounded-md bg-violet-50 px-2 py-0.5 text-[10px] font-semibold text-violet-900 sm:text-xs">
                DOCX
              </span>
            )}
            <div
              className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-semibold ring-1 sm:text-xs ${
                ooStatus?.enabled
                  ? 'bg-emerald-50 text-emerald-900 ring-emerald-200/80'
                  : 'bg-amber-50 text-amber-950 ring-amber-200/80'
              }`}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${ooStatus?.enabled ? 'bg-emerald-500' : 'bg-amber-500'}`}
              />
              OO
            </div>
            <button
              type="button"
              disabled={dlBusy}
              onClick={onDownload}
              title="Download template"
              aria-label={dlBusy ? 'Downloading…' : 'Download template'}
              className={`${btnSecondaryClass} !p-2`}
            >
              {dlBusy ? (
                <IconSpinner className="h-5 w-5 shrink-0 animate-spin text-slate-500" />
              ) : (
                <IconDownload className="h-5 w-5 shrink-0 text-slate-800" />
              )}
            </button>
            <button
              type="button"
              disabled={deletingId}
              onClick={onDelete}
              title="Delete template"
              aria-label={deletingId ? 'Deleting…' : 'Delete template'}
              className="inline-flex items-center justify-center rounded-xl border border-red-200/90 bg-white p-2 text-red-700 shadow-sm transition hover:bg-red-50 disabled:opacity-50"
            >
              {deletingId ? (
                <IconSpinner className="h-5 w-5 shrink-0 animate-spin text-red-500" />
              ) : (
                <IconTrash className="h-5 w-5 shrink-0" />
              )}
            </button>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 border-t border-slate-100 px-3 py-2 sm:px-4">
          <NavLink to={`/admin/templates/${templateId}/preview`} className={subTabClass}>
            Preview
          </NavLink>
          <NavLink to={`/admin/templates/${templateId}/edit`} className={subTabClass}>
            Edit
          </NavLink>
          <NavLink to={`/admin/templates/${templateId}/fields`} className={subTabClass}>
            Generated fields
          </NavLink>
        </div>

        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
          {template && detail ? (
            <Outlet context={outletContext} />
          ) : (
            <p className="p-4 text-sm text-slate-500">Loading…</p>
          )}
        </div>
      </div>
    </div>
  )
}
