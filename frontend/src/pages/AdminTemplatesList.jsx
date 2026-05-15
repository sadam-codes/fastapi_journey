import { useEffect, startTransition, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useConfirm } from '../components/ConfirmProvider.jsx'
import { toastError, toastSuccess } from '../toast.js'
import { btnSecondaryClass } from '../components/UserAreaLayout.jsx'

export default function AdminTemplatesList() {
  const confirm = useConfirm()
  const [templates, setTemplates] = useState([])
  const [ooStatus, setOoStatus] = useState(null)
  const [deletingId, setDeletingId] = useState(null)

  async function loadList() {
    try {
      const rows = await api('/forms/admin/templates')
      setTemplates(rows)
    } catch {
      setTemplates([])
    }
  }

  async function deleteTemplate(t) {
    const ok = await confirm({
      title: 'Delete template?',
      message: `Delete “${t.title}”? All user submissions for this template will be removed. This cannot be undone.`,
      confirmLabel: 'Delete',
      cancelLabel: 'Cancel',
      variant: 'danger',
    })
    if (!ok) return
    setDeletingId(t.id)
    try {
      await api(`/forms/admin/templates/${t.id}`, { method: 'DELETE' })
      toastSuccess('Template deleted.')
      await loadList()
    } catch (e) {
      toastError(e.message)
    } finally {
      setDeletingId(null)
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

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 border-b border-slate-200/80 pb-8 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">Templates</h1>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-slate-600">
            Open a template for preview or editing. DOCX files use OnlyOffice on the Edit page when the integration is
            enabled.
          </p>
        </div>
        <div
          className={`inline-flex shrink-0 items-center gap-2 self-start rounded-full px-3.5 py-2 text-xs font-semibold ring-1 ${
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

      {templates.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300/90 bg-slate-50/80 px-6 py-16 text-center">
          <p className="text-base font-semibold text-slate-800">No templates yet</p>
          <p className="mx-auto mt-2 max-w-md text-sm text-slate-600">
            Upload a PDF, DOCX, or image from the Upload page. Placeholders in{' '}
            <code className="rounded bg-white px-1 font-mono text-xs">{'{field}'}</code> form become user fields.
          </p>
          <Link to="/admin/upload" className={`mt-8 inline-flex ${btnSecondaryClass}`}>
            Upload a template
          </Link>
        </div>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {templates.map((t) => (
            <li
              key={t.id}
              className="flex h-full flex-col rounded-2xl border border-slate-200/90 bg-gradient-to-b from-white to-slate-50/80 shadow-sm shadow-slate-900/5 ring-1 ring-slate-900/[0.03] transition hover:border-indigo-300/80 hover:shadow-md hover:shadow-indigo-900/10"
            >
              <Link to={`/admin/templates/${t.id}`} className="group flex flex-1 flex-col p-5 pb-3">
                <div className="flex items-start justify-between gap-3">
                  <h2 className="min-w-0 flex-1 text-lg font-semibold leading-snug text-slate-900 group-hover:text-indigo-800">
                    {t.title}
                  </h2>
                  <span className="shrink-0 rounded-lg bg-indigo-50 px-2 py-1 text-xs font-bold text-indigo-800">
                    #{t.id}
                  </span>
                </div>
                <p className="mt-2 truncate text-sm text-slate-500">{t.original_filename}</p>
                <div className="mt-4 flex flex-wrap items-center gap-2">
                  <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700">
                    {t.field_count} label{t.field_count === 1 ? '' : 's'}
                  </span>
                  <span className="text-xs font-semibold text-indigo-600 group-hover:underline">Open →</span>
                </div>
              </Link>
              <div className="flex items-center justify-end gap-2 border-t border-slate-200/80 px-5 py-3">
                <button
                  type="button"
                  disabled={deletingId === t.id}
                  onClick={() => deleteTemplate(t)}
                  className="rounded-lg border border-rose-200/90 bg-white px-3 py-1.5 text-xs font-semibold text-rose-700 shadow-sm hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-50 sm:text-sm"
                >
                  {deletingId === t.id ? 'Deleting…' : 'Delete'}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
