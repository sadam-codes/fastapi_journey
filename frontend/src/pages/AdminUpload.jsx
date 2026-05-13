import { useCallback, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getToken } from '../api'
import { toastError, toastSuccess, toastWarning } from '../toast.js'
import { btnPrimaryClass, GlassCard } from '../components/UserAreaLayout.jsx'

const ACCEPT = '.pdf,.docx,.png,.jpg,.jpeg,.webp,.gif,.tiff,.bmp'

function formatBytes(n) {
  if (n == null || Number.isNaN(n)) return ''
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(n < 10_240 ? 1 : 0)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

function IconCloud({ className }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" aria-hidden>
      <path
        fill="currentColor"
        d="M8.5 7.5A4.5 4.5 0 0 1 17 7c.3 0 .6 0 .9.1A3.5 3.5 0 0 1 17 17h-1.5a.75.75 0 0 1 0-1.5H17a2 2 0 1 0-.2-4 .75.75 0 0 1-.74-.65A3 3 0 1 0 8 9.25a.75.75 0 0 1-.75.75A2.75 2.75 0 1 0 8.5 16H10a.75.75 0 0 1 0 1.5H8.5a4.25 4.25 0 0 1 0-8.5Z"
      />
      <path
        fill="currentColor"
        d="M12 12.25a.75.75 0 0 1 .75.75v3.19l1-1a.75.75 0 0 1 1.06 1.06l-2.25 2.25a.75.75 0 0 1-1.06 0L9.25 16.25a.75.75 0 0 1 1.06-1.06l1 1V13a.75.75 0 0 1 .69-.75Z"
      />
    </svg>
  )
}

function IconDoc({ className }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" aria-hidden>
      <path
        stroke="currentColor"
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
      />
    </svg>
  )
}

export default function AdminUpload() {
  const navigate = useNavigate()
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef(null)

  const pickFiles = useCallback((list) => {
    const f = list?.[0]
    if (f) setFile(f)
  }, [])

  function clearFile() {
    setFile(null)
    if (inputRef.current) inputRef.current.value = ''
  }

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
      toastSuccess(data.message || 'Template saved.')
      setFile(null)
      if (inputRef.current) inputRef.current.value = ''
      if (data.id) {
        navigate(`/admin/templates/${data.id}`, { replace: false })
      }
    } catch (ex) {
      toastError(ex.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto w-full max-w-md py-8 sm:py-10">
      <h1 className="text-center text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">Upload template</h1>
      <p className="mt-1 text-center text-sm text-slate-500">PDF, DOCX, or image · up to 15 MB</p>

      <GlassCard className="mt-6 overflow-hidden !p-0 sm:!p-0">
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
            className={`flex w-full flex-col items-center px-4 py-12 text-center transition sm:py-14 ${
              dragOver
                ? 'bg-indigo-50 ring-2 ring-inset ring-indigo-300/70'
                : 'bg-slate-50/70 hover:bg-indigo-50/50'
            }`}
          >
            <span
              className={`flex h-14 w-14 items-center justify-center rounded-2xl shadow-md transition ${
                dragOver
                  ? 'scale-105 bg-indigo-600 text-white shadow-indigo-500/30'
                  : 'bg-white text-indigo-600 ring-1 ring-slate-200/90'
              }`}
            >
              <IconCloud className="h-7 w-7" />
            </span>
            <span className="mt-4 text-sm font-semibold text-slate-900">Drop a file or click to browse</span>
            {file ? (
              <div className="mt-5 w-full max-w-sm">
                <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-left shadow-sm">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-700">
                    <IconDoc className="h-5 w-5" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-900" title={file.name}>
                      {file.name}
                    </p>
                    <p className="text-xs text-slate-500">{formatBytes(file.size)}</p>
                  </div>
                  <button
                    type="button"
                    onClick={(ev) => {
                      ev.stopPropagation()
                      clearFile()
                    }}
                    className="shrink-0 rounded-lg px-2.5 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  >
                    Remove
                  </button>
                </div>
              </div>
            ) : null}
          </button>

          <div className="border-t border-slate-200/80 p-4 sm:px-5">
            <button type="submit" disabled={busy} className={`${btnPrimaryClass} w-full justify-center`}>
              {busy ? 'Uploading…' : 'Upload'}
            </button>
          </div>
        </form>
      </GlassCard>
    </div>
  )
}
