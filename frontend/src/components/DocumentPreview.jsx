import { useEffect, useState } from 'react'
import { fetchSubmissionFilledPreview, fetchTemplatePreview } from '../api'
import OnlyOfficeDocx from './OnlyOfficeDocx.jsx'

const IMAGE_EXT = new Set(['.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.tif', '.tiff'])

function fileExt(name) {
  if (!name || typeof name !== 'string') return ''
  const i = name.lastIndexOf('.')
  return i >= 0 ? name.slice(i).toLowerCase() : ''
}

function isDocx(name) {
  return fileExt(name) === '.docx'
}

function LegacyBlobPreview({
  templateId,
  submissionId,
  filename,
  revision,
  fillHeight = false,
}) {
  const [phase, setPhase] = useState('loading')
  const [hint, setHint] = useState('')
  const [blobUrl, setBlobUrl] = useState(null)

  useEffect(() => {
    let alive = true
    let objectUrl = null

    async function load() {
      setPhase('loading')
      setHint('')
      setBlobUrl(null)
      try {
        const { blob, contentType } =
          submissionId != null
            ? await fetchSubmissionFilledPreview(submissionId, revision)
            : await fetchTemplatePreview(templateId, revision)
        if (!alive) return
        const ex = fileExt(filename)
        const ct = (contentType || blob.type || '').toLowerCase()
        const pdfish = ex === '.pdf' || ct.includes('application/pdf')
        const imgish = IMAGE_EXT.has(ex) || ct.startsWith('image/')
        if (pdfish) {
          objectUrl = URL.createObjectURL(blob)
          setBlobUrl(objectUrl)
          setPhase('pdf')
          return
        }
        if (imgish) {
          objectUrl = URL.createObjectURL(blob)
          setBlobUrl(objectUrl)
          setPhase('image')
          return
        }
        setPhase('unsupported')
        setHint('Preview supports DOCX (OnlyOffice), PDF, and common images.')
      } catch (e) {
        if (!alive) return
        setPhase('error')
        setHint(e.message || 'Could not load preview.')
      }
    }
    load()
    return () => {
      alive = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [templateId, submissionId, filename, revision])

  if (phase === 'loading') {
    return (
      <div className="flex min-h-[280px] items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50/90 text-sm text-slate-600">
        Loading preview…
      </div>
    )
  }

  if (phase === 'error') {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{hint}</div>
    )
  }

  if (phase === 'unsupported') {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">{hint}</div>
    )
  }

  if (phase === 'pdf' && blobUrl) {
    return (
      <div
        className={
          fillHeight
            ? 'flex h-full min-h-0 flex-1 flex-col overflow-hidden bg-slate-200/40'
            : 'overflow-hidden rounded-xl border border-slate-200 bg-slate-200/40 shadow-inner'
        }
      >
        <iframe
          title="PDF preview"
          src={blobUrl}
          className={
            fillHeight ? 'min-h-0 w-full flex-1 border-0 bg-white' : 'h-[min(70vh,720px)] w-full bg-white'
          }
        />
      </div>
    )
  }

  if (phase === 'image' && blobUrl) {
    return (
      <div
        className={
          fillHeight
            ? 'flex h-full min-h-0 flex-1 items-center justify-center overflow-auto bg-slate-100 p-4'
            : 'flex max-h-[min(70vh,720px)] justify-center overflow-auto rounded-xl border border-slate-200 bg-slate-50 p-4 shadow-inner'
        }
      >
        <img src={blobUrl} alt="Document preview" className="max-h-full max-w-full object-contain" />
      </div>
    )
  }

  return null
}

/**
 * Preview original template or merged submission: .docx via ONLYOFFICE; PDF iframe; images inline.
 * Pass either `templateId` OR `submissionId` (admin filled file).
 */
export default function DocumentPreview({
  templateId,
  submissionId,
  filename,
  revision = 0,
  onlyOfficeAdmin = true,
  fillHeight = false,
}) {
  const useSubmission = submissionId != null

  if (isDocx(filename)) {
    const editor = (
      <OnlyOfficeDocx
        templateId={useSubmission ? undefined : templateId}
        submissionId={useSubmission ? submissionId : undefined}
        mode="view"
        admin={onlyOfficeAdmin}
        revision={revision}
        className={
          fillHeight
            ? 'min-h-0 flex-1 rounded-none border-0 bg-slate-100 shadow-none'
            : 'h-[min(72vh,780px)] min-h-[360px]'
        }
      />
    )
    if (fillHeight) {
      return <div className="flex min-h-[calc(100svh-10.5rem)] w-full flex-1 flex-col">{editor}</div>
    }
    return editor
  }

  return (
    <LegacyBlobPreview
      templateId={useSubmission ? undefined : templateId}
      submissionId={useSubmission ? submissionId : undefined}
      filename={filename}
      revision={revision}
      fillHeight={fillHeight}
    />
  )
}
