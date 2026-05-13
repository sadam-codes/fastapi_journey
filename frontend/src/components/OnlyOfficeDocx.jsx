import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react'
import { getToken } from '../api'

const apiBase = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

const sdkPromises = new Map()

function loadSdkOnce(sdkUrl) {
  if (typeof window !== 'undefined' && window.DocsAPI) {
    return Promise.resolve()
  }
  if (!sdkPromises.has(sdkUrl)) {
    sdkPromises.set(
      sdkUrl,
      new Promise((resolve, reject) => {
        const esc = sdkUrl.replace(/"/g, '\\"')
        const existing = document.querySelector(`script[src="${esc}"]`)
        if (existing && window.DocsAPI) {
          resolve()
          return
        }
        const s = document.createElement('script')
        s.src = sdkUrl
        s.async = true
        s.onload = () => resolve()
        s.onerror = () => {
          sdkPromises.delete(sdkUrl)
          reject(new Error('Could not load OnlyOffice script. Check Document Server URL.'))
        }
        document.head.appendChild(s)
      }),
    )
  }
  return sdkPromises.get(sdkUrl)
}

async function fetchBootstrap(templateId, submissionId, mode, admin, viewCacheBust = 0) {
  let url
  if (submissionId != null) {
    url = `${apiBase}/forms/admin/submissions/${submissionId}/onlyoffice/bootstrap?mode=${encodeURIComponent(mode)}&v=${encodeURIComponent(String(viewCacheBust))}`
  } else {
    const path = admin
      ? `/forms/admin/templates/${templateId}/onlyoffice/bootstrap`
      : `/forms/templates/${templateId}/onlyoffice/bootstrap`
    url = `${apiBase}${path}?mode=${encodeURIComponent(mode)}`
    if (mode === 'view') {
      url += `&v=${encodeURIComponent(String(viewCacheBust))}`
    }
  }
  const ctrl = new AbortController()
  const abortT = window.setTimeout(() => ctrl.abort(), 60_000)
  let res
  try {
    res = await fetch(url, {
      headers: { Authorization: `Bearer ${getToken()}` },
      cache: 'no-store',
      signal: ctrl.signal,
    })
  } catch (e) {
    if (e?.name === 'AbortError') {
      throw new Error('Timed out waiting for OnlyOffice config from the API (60s).')
    }
    throw e
  } finally {
    window.clearTimeout(abortT)
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const d = data.detail
    const msg = Array.isArray(d)
      ? d.map((x) => (typeof x === 'object' && x.msg ? x.msg : String(x))).join(', ')
      : d || res.statusText
    throw new Error(msg || `HTTP ${res.status}`)
  }
  return data
}

/**
 * ONLYOFFICE Docs editor or viewer for .docx templates or admin merged submissions.
 */
export default function OnlyOfficeDocx({
  templateId,
  submissionId,
  mode,
  admin,
  revision = 0,
  className = '',
  onReady,
  onError,
}) {
  const rid = useId().replace(/:/g, '')
  const containerId = useMemo(() => {
    const base =
      submissionId != null
        ? `oo_sub_${submissionId}_${mode}_${revision}_${rid}`
        : `oo_${templateId}_${mode}_${revision}_${rid}`
    return base.replace(/[^a-zA-Z0-9_-]/g, '_')
  }, [templateId, submissionId, mode, revision, rid])
  const hostRef = useRef(null)
  const editorRef = useRef(null)
  const onReadyRef = useRef(onReady)
  const onErrorRef = useRef(onError)

  useEffect(() => {
    onReadyRef.current = onReady
    onErrorRef.current = onError
  }, [onReady, onError])

  const [phase, setPhase] = useState('loading')
  const [hint, setHint] = useState('')
  /** Where time is spent while phase === 'loading' (helps debug stuck opens). */
  const [loadStep, setLoadStep] = useState('config')

  const tearDown = useCallback(() => {
    const ed = editorRef.current
    editorRef.current = null
    if (ed && typeof ed.destroyEditor === 'function') {
      try {
        ed.destroyEditor()
      } catch {
        /* ignore */
      }
    }
    const el = hostRef.current
    if (el) {
      el.innerHTML = ''
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    let stallTimer = 0
    let documentReady = false

    async function run() {
      setPhase('loading')
      setLoadStep('config')
      setHint('')
      tearDown()

      try {
        if (
          submissionId == null &&
          (templateId == null || Number.isNaN(Number(templateId)))
        ) {
          throw new Error('Missing template for OnlyOffice.')
        }
        if (submissionId != null && Number.isNaN(Number(submissionId))) {
          throw new Error('Invalid submission for OnlyOffice.')
        }
        const boot = await fetchBootstrap(templateId, submissionId, mode, admin, mode === 'view' ? revision : 0)
        if (cancelled) return

        if (!boot.available) {
          setPhase('unavailable')
          setHint(boot.message || 'OnlyOffice is not configured.')
          return
        }

        if (!boot.sdkUrl || !boot.config) {
          setPhase('unavailable')
          setHint('Invalid bootstrap response from server.')
          return
        }

        setLoadStep('sdk')
        await loadSdkOnce(boot.sdkUrl)
        if (cancelled) return
        if (!window.DocsAPI) {
          throw new Error('OnlyOffice API not available after loading script.')
        }

        setLoadStep('document')
        const el = hostRef.current
        if (!el) {
          throw new Error('Editor area not mounted. Try refreshing the page.')
        }
        el.innerHTML = `<div id="${containerId}" class="h-full w-full min-h-0" style="height:100%"></div>`

        const cfg = JSON.parse(JSON.stringify(boot.config))
        cfg.events = {
          ...(cfg.events && typeof cfg.events === 'object' ? cfg.events : {}),
          onDocumentReady: () => {
            if (cancelled) return
            documentReady = true
            window.clearTimeout(stallTimer)
            stallTimer = 0
            setPhase('ready')
            onReadyRef.current?.()
          },
          onError: (event) => {
            if (cancelled) return
            window.clearTimeout(stallTimer)
            stallTimer = 0
            const msg = event?.data || event?.message || 'OnlyOffice error'
            const s = String(msg)
            setPhase('error')
            setHint(s)
            onErrorRef.current?.(s)
          },
        }
        if (boot.token) {
          cfg.token = boot.token
        }

        stallTimer = window.setTimeout(() => {
          if (cancelled || documentReady) return
          setHint(
            'The document did not finish loading in time. Check the browser console, Document Server logs, and that JWT / PUBLIC_APP_URL match your setup.',
          )
          setPhase('error')
        }, 120_000)

        const editor = new window.DocsAPI.DocEditor(containerId, cfg)
        editorRef.current = editor
      } catch (e) {
        if (cancelled) return
        window.clearTimeout(stallTimer)
        const msg = e?.message || String(e)
        setPhase('error')
        setHint(msg)
        onErrorRef.current?.(msg)
      }
    }

    run()
    return () => {
      cancelled = true
      window.clearTimeout(stallTimer)
      tearDown()
    }
  }, [templateId, submissionId, mode, admin, revision, containerId, tearDown])

  return (
    <div
      className={`relative flex min-h-0 flex-col overflow-hidden rounded-xl border border-slate-200/90 bg-slate-50 shadow-inner ${className}`}
    >
      {phase === 'loading' && (
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-white/85 backdrop-blur-[2px]">
          <div
            className="h-9 w-9 animate-spin rounded-full border-2 border-indigo-200 border-t-indigo-600"
            aria-hidden
          />
          <p className="text-sm font-medium text-slate-600">Opening document…</p>
          <p className="max-w-sm px-4 text-center text-xs leading-relaxed text-slate-500">
            {loadStep === 'config' && 'Getting editor settings from your API.'}
            {loadStep === 'sdk' && 'Loading OnlyOffice from the Document Server (can take a while the first time).'}
            {loadStep === 'document' &&
              'loading...'}
          </p>
        </div>
      )}
      {phase === 'unavailable' && (
        <div className="flex min-h-[280px] flex-col items-center justify-center gap-3 bg-gradient-to-b from-amber-50/90 to-white p-8 text-center">
          <p className="text-sm font-semibold text-amber-950">OnlyOffice not available</p>
          <p className="max-w-md text-sm leading-relaxed text-amber-900/90">{hint}</p>
        </div>
      )}
      {phase === 'error' && (
        <div className="flex min-h-[220px] items-center justify-center p-6">
          <p className="max-w-lg text-center text-sm text-red-800">{hint}</p>
        </div>
      )}
      <div
        ref={hostRef}
        className={`relative z-0 min-h-0 flex-1 basis-0 overflow-hidden w-full ${phase === 'ready' || phase === 'loading' ? '' : 'hidden'}`}
        style={{ minHeight: 'max(360px, calc(100svh - 11rem))' }}
      />
    </div>
  )
}
