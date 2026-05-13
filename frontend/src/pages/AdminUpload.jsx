import { useCallback, useRef, useState } from 'react'
import { getToken } from '../api'
import { toastError, toastSuccess, toastWarning } from '../toast.js'
import { btnPrimaryClass, GlassCard } from '../components/UserAreaLayout.jsx'

const ACCEPT = '.pdf,.docx,.png,.jpg,.jpeg,.webp,.gif,.tiff,.bmp'

export default function AdminUpload() {
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef(null)

  const pickFiles = useCallback((list) => {
    const f = list?.[0]
    if (f) setFile(f)
  }, [])

  async function onUpload(e) {
    e.preventDefault()
    if (!file) {
      toastWarning('Choose a file first, or drop it into the upload area.')
      return
    }
    setBusy(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const base = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'
      const res = await fetch(`${base}/forms/admin/upload`, {
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
      toastSuccess('Uploaded successfully.')
      setFile(null)
    } catch (ex) {
      toastError(ex.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-[50vh] items-center justify-center py-8">
      <GlassCard className="w-full max-w-lg overflow-hidden !p-0 sm:!p-0">
        <form onSubmit={onUpload}>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT}
            className="sr-only"
            onChange={(e) => pickFiles(e.target.files)}
          />
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            onDragEnter={(e) => {
              e.preventDefault()
              setDragOver(true)
            }}
            onDragLeave={(e) => {
              e.preventDefault()
              if (!e.currentTarget.contains(e.relatedTarget)) setDragOver(false)
            }}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault()
              setDragOver(false)
              pickFiles(e.dataTransfer.files)
            }}
            className={`flex w-full flex-col items-center justify-center px-6 py-16 text-center transition sm:py-20 ${
              dragOver
                ? 'bg-indigo-50/90 ring-2 ring-inset ring-indigo-300/80'
                : 'bg-slate-50/50 hover:bg-indigo-50/40'
            }`}
          >
            <span className="text-base font-semibold text-slate-900">Drop file here</span>
            <span className="mt-2 text-sm text-slate-500">or click to choose a file</span>
            {file ? (
              <span
                className="mt-6 inline-flex max-w-full items-center gap-2 rounded-full bg-white px-4 py-2 text-sm font-medium text-slate-800 shadow-sm ring-1 ring-slate-200/80"
                title={file.name}
              >
                <span className="truncate">{file.name}</span>
                <span className="shrink-0 rounded-md bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-600">
                  {(file.size / 1024).toFixed(0)} KB
                </span>
              </span>
            ) : null}
          </button>
          <div className="border-t border-slate-200/80 p-4 sm:p-5">
            <button type="submit" disabled={busy} className={`${btnPrimaryClass} w-full justify-center`}>
              {busy ? 'Uploading…' : 'Upload'}
            </button>
          </div>
        </form>
      </GlassCard>
    </div>
  )
}
