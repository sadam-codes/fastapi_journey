import { useEffect, startTransition, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { toastError } from '../toast.js'
import { btnSecondaryClass } from '../components/UserAreaLayout.jsx'

function formatWhen(iso) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
  } catch {
    return String(iso)
  }
}

export default function AdminSubmissionsList() {
  const [rows, setRows] = useState([])
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    startTransition(() => {
      ;(async () => {
        try {
          setFailed(false)
          const data = await api('/forms/admin/submissions')
          setRows(data)
        } catch (e) {
          setFailed(true)
          toastError(e.message)
          setRows([])
        }
      })()
    })
  }, [])

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 border-b border-slate-200/80 pb-8 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">Filled forms</h1>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-600">
            Every submission from the user site appears here. Open a row to see answers and download the merged file.
          </p>
        </div>
        <Link to="/admin/templates" className={`${btnSecondaryClass} shrink-0 self-start`}>
          Templates
        </Link>
      </div>

      {failed && rows.length === 0 ? (
        <p className="text-sm text-slate-600">Could not load submissions.</p>
      ) : rows.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300/90 bg-slate-50/80 px-6 py-16 text-center">
          <p className="text-base font-semibold text-slate-800">No submissions yet</p>
          <p className="mx-auto mt-2 max-w-md text-sm text-slate-600">
            When users complete a form from the user portal, it will show up in this list.
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-50/90 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3 sm:px-5">Form</th>
                <th className="hidden px-4 py-3 sm:table-cell sm:px-5">User</th>
                <th className="hidden px-4 py-3 md:table-cell md:px-5">Submitted</th>
                <th className="px-4 py-3 sm:px-5" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((r) => (
                <tr key={r.id} className="bg-white/80 hover:bg-indigo-50/40">
                  <td className="px-4 py-3 sm:px-5">
                    <p className="font-semibold text-slate-900">{r.template_title}</p>
                    <p className="mt-0.5 truncate text-xs text-slate-500 sm:hidden">{r.user_email}</p>
                    <p className="mt-0.5 truncate text-xs text-slate-500 md:hidden">{formatWhen(r.created_at)}</p>
                    {r.filled_filename ? (
                      <p className="mt-1 truncate text-xs text-slate-500" title={r.filled_filename}>
                        {r.filled_filename}
                      </p>
                    ) : null}
                  </td>
                  <td className="hidden px-4 py-3 sm:table-cell sm:px-5">
                    <p className="font-medium text-slate-800">{r.user_email}</p>
                    {r.user_name ? <p className="text-xs text-slate-500">{r.user_name}</p> : null}
                  </td>
                  <td className="hidden whitespace-nowrap px-4 py-3 text-slate-600 md:table-cell md:px-5">
                    {formatWhen(r.created_at)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right sm:px-5">
                    <Link
                      to={`/admin/submissions/${r.id}`}
                      className="inline-flex rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white shadow-sm hover:bg-indigo-500 sm:text-sm"
                    >
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
