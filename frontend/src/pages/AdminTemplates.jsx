import { useCallback, useEffect, startTransition, useState } from 'react'
import { api, downloadAdminTemplate, updateAdminTemplate } from '../api'
import DocumentPreview from '../components/DocumentPreview.jsx'
import OnlyOfficeDocx from '../components/OnlyOfficeDocx.jsx'
import {
  btnPrimaryClass,
  btnSecondaryClass,
  fileInputClass,
  userAreaInputClass,
} from '../components/UserAreaLayout.jsx'

function isDocxFilename(name) {
  return typeof name === 'string' && name.toLowerCase().endsWith('.docx')
}

export default function AdminTemplates() {
  const [templates, setTemplates] = useState([])
  const [openPreviewId, setOpenPreviewId] = useState(null)
  const [detailById, setDetailById] = useState({})
  const [deletingId, setDeletingId] = useState(null)
  const [dlBusy, setDlBusy] = useState(null)
  const [err, setErr] = useState('')
  const [okMsg, setOkMsg] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [editTitle, setEditTitle] = useState('')
  const [editFile, setEditFile] = useState(null)
  const [editBusy, setEditBusy] = useState(false)
  const [previewRevById, setPreviewRevById] = useState({})
  const [editOoKey, setEditOoKey] = useState(0)
  const [ooStatus, setOoStatus] = useState(null)

  const bumpPreview = useCallback((templateId) => {
    setPreviewRevById((prev) => ({
      ...prev,
      [templateId]: (prev[templateId] || 0) + 1,
    }))
  }, [])

  async function loadList() {
    try {
      const rows = await api('/forms/admin/templates')
      setTemplates(rows)
    } catch {
      setTemplates([])
    }
  }

  useEffect(() => {
    startTransition(() => {
      void loadList()
    })
  }, [])

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
    if (!templates.length) return
    let cancelled = false
    ;(async () => {
      const next = {}
      for (const t of templates) {
        try {
          const d = await api(`/forms/admin/templates/${t.id}`)
          if (!cancelled) next[t.id] = d
        } catch {
          /* ignore */
        }
      }
      if (!cancelled) setDetailById(next)
    })()
    return () => {
      cancelled = true
    }
  }, [templates])

  async function onDeleteTemplate(templateId) {
    if (
      !window.confirm(
        'Delete this template? All user submissions for it will be removed. This cannot be undone.',
      )
    ) {
      return
    }
    setErr('')
    setOkMsg('')
    setDeletingId(templateId)
    try {
      await api(`/forms/admin/templates/${templateId}`, { method: 'DELETE' })
      setOpenPreviewId((cur) => (cur === templateId ? null : cur))
      setEditingId((cur) => (cur === templateId ? null : cur))
      setDetailById((prev) => {
        const next = { ...prev }
        delete next[templateId]
        return next
      })
      await loadList()
    } catch (ex) {
      setErr(ex.message)
    } finally {
      setDeletingId(null)
    }
  }

  async function onDownload(id, filename) {
    setErr('')
    setOkMsg('')
    setDlBusy(id)
    try {
      await downloadAdminTemplate(id, filename)
    } catch (ex) {
      setErr(ex.message)
    } finally {
      setDlBusy(null)
    }
  }

  function togglePreview(id) {
    setOpenPreviewId((cur) => (cur === id ? null : id))
  }

  function startEdit(t) {
    const d = detailById[t.id]
    setErr('')
    setOkMsg('')
    setEditingId(t.id)
    setEditTitle(d?.title ?? t.title)
    setEditFile(null)
    if (isDocxFilename(t.original_filename)) {
      setEditOoKey((k) => k + 1)
    }
  }

  function cancelEdit() {
    const id = editingId
    const tmpl = id ? templates.find((x) => x.id === id) : null
    const wasDocx = tmpl && isDocxFilename(tmpl.original_filename)
    setEditingId(null)
    setEditFile(null)
    setEditBusy(false)
    if (id && wasDocx) {
      bumpPreview(id)
    }
    void loadList()
  }

  async function onSaveMetadata(templateId) {
    const tmpl = templates.find((x) => x.id === templateId)
    const currentTitle = (detailById[templateId]?.title ?? tmpl?.title ?? '').trim()
    const titleChanged = editTitle.trim() !== currentTitle

    setErr('')
    setOkMsg('')

    if (!editFile && !titleChanged) {
      setErr('Change the display title or choose a replacement file.')
      return
    }

    setEditBusy(true)
    try {
      const data2 = await updateAdminTemplate(templateId, {
        title: editTitle,
        file: editFile || undefined,
      })
      setOkMsg(data2.message || 'Saved.')
      setDetailById((prev) => ({
        ...prev,
        [templateId]: {
          id: data2.id,
          title: data2.title,
          original_filename: data2.original_filename,
          fields_schema: data2.fields_schema || [],
          created_at: prev[templateId]?.created_at,
        },
      }))
      setEditFile(null)
      bumpPreview(templateId)
      await loadList()
    } catch (ex) {
      setErr(ex.message)
    } finally {
      setEditBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 border-b border-slate-200/80 pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">Templates</h2>
          <p className="mt-1 text-sm text-slate-600">
            DOCX: preview and edit in OnlyOffice. Rename or replace files from the Upload tab.
          </p>
        </div>
        <div
          className={`inline-flex shrink-0 items-center gap-2 self-start rounded-full px-3 py-1.5 text-xs font-semibold ring-1 ${
            ooStatus?.enabled
              ? 'bg-emerald-50 text-emerald-900 ring-emerald-200/80'
              : 'bg-amber-50 text-amber-950 ring-amber-200/80'
          }`}
        >
          <span
            className={`h-2 w-2 rounded-full ${ooStatus?.enabled ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.7)]' : 'bg-amber-500'}`}
          />
          {ooStatus?.enabled ? 'OnlyOffice connected' : 'OnlyOffice not configured'}
        </div>
      </div>

      {err && (
        <p className="rounded-xl border border-red-200/90 bg-red-50 px-4 py-3 text-sm text-red-900 shadow-sm">{err}</p>
      )}
      {okMsg && (
        <p className="rounded-xl border border-emerald-200/90 bg-emerald-50 px-4 py-3 text-sm text-emerald-950 shadow-sm">
          {okMsg}
        </p>
      )}

      <div>
        {templates.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300/90 bg-slate-50/80 px-6 py-14 text-center">
            <p className="text-sm font-medium text-slate-700">No templates yet</p>
            <p className="mx-auto mt-2 max-w-sm text-sm text-slate-500">
              Upload a file from the Upload tab. DOCX files will use OnlyOffice once the server URL is set.
            </p>
          </div>
        ) : (
          <ul className="space-y-4">
            {templates.map((t) => {
              const docx = isDocxFilename(t.original_filename)
              return (
                <li
                  key={t.id}
                  className="overflow-hidden rounded-2xl border border-slate-200/90 bg-white/90 shadow-sm shadow-slate-900/5 ring-1 ring-slate-900/[0.03] backdrop-blur-sm"
                >
                  <div className="flex flex-col gap-4 p-5 sm:flex-row sm:items-start sm:justify-between sm:p-6">
                    <div className="min-w-0 flex-1">
                      <h3 className="truncate text-lg font-semibold text-slate-900">{t.title}</h3>
                      <p className="mt-1 truncate text-sm text-slate-500">{t.original_filename}</p>
                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        <span className="rounded-md bg-slate-100 px-2 py-0.5 font-mono text-[11px] font-medium uppercase tracking-wide text-slate-600">
                          id {t.id}
                        </span>
                        <span className="rounded-md bg-indigo-50 px-2 py-0.5 text-xs font-semibold text-indigo-800">
                          {t.field_count} merge field{t.field_count === 1 ? '' : 's'}
                        </span>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2 sm:shrink-0 sm:justify-end">
                      <button
                        type="button"
                        className={`${btnSecondaryClass} py-2.5 text-xs font-semibold`}
                        onClick={() => togglePreview(t.id)}
                      >
                        {openPreviewId === t.id ? 'Hide preview' : 'Preview'}
                      </button>
                      <button
                        type="button"
                        className={`${btnSecondaryClass} py-2.5 text-xs font-semibold`}
                        onClick={() => startEdit(t)}
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        className={`${btnSecondaryClass} py-2.5 text-xs font-semibold`}
                        disabled={dlBusy === t.id}
                        onClick={() => onDownload(t.id, t.original_filename)}
                      >
                        {dlBusy === t.id ? 'Downloading…' : 'Download'}
                      </button>
                      <button
                        type="button"
                        disabled={deletingId === t.id}
                        className="inline-flex items-center justify-center rounded-xl border border-red-200/90 bg-white px-3 py-2.5 text-xs font-semibold text-red-700 shadow-sm transition hover:bg-red-50 disabled:opacity-50"
                        onClick={() => onDeleteTemplate(t.id)}
                      >
                        {deletingId === t.id ? 'Deleting…' : 'Delete'}
                      </button>
                    </div>
                  </div>

                  {openPreviewId === t.id && (
                    <div className="border-t border-slate-200/80 bg-slate-50/50 px-4 py-4 sm:px-6 sm:py-5">
                      <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Document preview</p>
                        <button
                          type="button"
                          onClick={() => bumpPreview(t.id)}
                          className="self-start rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm transition hover:border-indigo-200 hover:text-indigo-800 sm:self-auto"
                        >
                          Reload preview
                        </button>
                      </div>
                      <DocumentPreview
                        templateId={t.id}
                        filename={t.original_filename}
                        revision={previewRevById[t.id] || 0}
                        onlyOfficeAdmin
                      />
                    </div>
                  )}

                  {editingId === t.id && (
                    <div className="border-t border-slate-200/80 bg-white px-4 py-4 sm:px-6 sm:py-5">
                      {docx ? (
                        <div className="space-y-3">
                          <div className="flex items-center justify-between gap-3">
                            <h4 className="text-base font-semibold text-slate-900">Edit template</h4>
                            <button type="button" className={btnSecondaryClass} onClick={cancelEdit}>
                              Close
                            </button>
                          </div>
                          <div className="min-h-0 overflow-hidden rounded-xl border border-slate-200/90 bg-white shadow-sm">
                            <OnlyOfficeDocx
                              templateId={t.id}
                              mode="edit"
                              admin
                              revision={editOoKey}
                              className="h-[min(88vh,920px)] min-h-[480px]"
                              onReady={() => setOkMsg('')}
                            />
                          </div>
                        </div>
                      ) : (
                        <>
                          <div className="mb-4">
                            <h4 className="text-base font-semibold text-slate-900">Edit template</h4>
                          </div>
                        <div className="mx-auto max-w-xl space-y-5">
                          <p className="text-sm text-amber-950">
                            OnlyOffice is for .docx. Update the title or replace the file below, or download to edit
                            elsewhere.
                          </p>
                          <label className="block text-sm font-medium text-slate-800">
                            Display title
                            <input
                              value={editTitle}
                              onChange={(e) => setEditTitle(e.target.value)}
                              className={`${userAreaInputClass} mt-1.5`}
                            />
                          </label>
                          <details className="rounded-lg border border-slate-200/80 bg-white/80 p-3">
                            <summary className="cursor-pointer text-sm font-semibold text-slate-800">Replace file</summary>
                            <input
                              type="file"
                              accept=".pdf,.docx,.png,.jpg,.jpeg,.webp,.gif,.tiff,.bmp"
                              onChange={(e) => setEditFile(e.target.files?.[0] || null)}
                              className={`${fileInputClass} mt-2`}
                            />
                          </details>
                          <div className="flex flex-wrap gap-2">
                            <button
                              type="button"
                              disabled={editBusy}
                              className={btnPrimaryClass}
                              onClick={() => onSaveMetadata(t.id)}
                            >
                              {editBusy ? 'Saving…' : 'Save changes'}
                            </button>
                            <button type="button" className={btnSecondaryClass} disabled={editBusy} onClick={cancelEdit}>
                              Cancel
                            </button>
                          </div>
                        </div>
                        </>
                      )}
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}
