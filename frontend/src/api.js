const base = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

export function getToken() {
  return localStorage.getItem('token')
}

export function setToken(t) {
  if (t) localStorage.setItem('token', t)
  else localStorage.removeItem('token')
}

export async function api(path, { method = 'GET', body, headers = {} } = {}) {
  const token = getToken()
  const h = { ...headers }
  if (token) h.Authorization = `Bearer ${token}`
  if (body !== undefined && !(body instanceof FormData)) {
    h['Content-Type'] = 'application/json'
  }
  const res = await fetch(`${base}${path}`, {
    method,
    headers: h,
    body: body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
  })
  const text = await res.text()
  let data
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = text
  }
  if (!res.ok) {
    let msg = res.statusText
    if (typeof data === 'object' && data && data.detail) {
      if (Array.isArray(data.detail)) {
        msg = data.detail
          .map((d) => (typeof d === 'object' && d.msg ? d.msg : String(d)))
          .join(', ')
      } else {
        msg = String(data.detail)
      }
    }
    throw new Error(msg || `HTTP ${res.status}`)
  }
  return data
}

/** Binary template file for in-browser preview (auth required). */
export async function fetchTemplatePreview(templateId, revision = 0) {
  const token = getToken()
  const qs = new URLSearchParams()
  if (revision != null) qs.set('v', String(revision))
  const q = qs.toString() ? `?${qs.toString()}` : ''
  const res = await fetch(`${base}/forms/templates/${templateId}/preview${q}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: 'no-store',
  })
  if (!res.ok) {
    const text = await res.text()
    let msg = res.statusText
    try {
      const data = text ? JSON.parse(text) : null
      if (typeof data === 'object' && data && data.detail) {
        msg = Array.isArray(data.detail)
          ? data.detail.map((d) => (typeof d === 'object' && d.msg ? d.msg : String(d))).join(', ')
          : String(data.detail)
      }
    } catch {
      if (text) msg = text.slice(0, 200)
    }
    throw new Error(msg || `HTTP ${res.status}`)
  }
  const blob = await res.blob()
  const contentType = res.headers.get('content-type') || blob.type || ''
  return { blob, contentType }
}

/** Admin: download original template file for editing locally. */
export async function downloadAdminTemplate(templateId, fallbackFilename = '') {
  const token = getToken()
  const res = await fetch(`${base}/forms/admin/templates/${templateId}/download`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) {
    const text = await res.text()
    let msg = res.statusText
    try {
      const data = text ? JSON.parse(text) : null
      if (typeof data === 'object' && data && data.detail) {
        msg = Array.isArray(data.detail)
          ? data.detail.map((d) => (typeof d === 'object' && d.msg ? d.msg : String(d))).join(', ')
          : String(data.detail)
      }
    } catch {
      if (text) msg = text.slice(0, 200)
    }
    throw new Error(msg || `HTTP ${res.status}`)
  }
  const blob = await res.blob()
  let name = fallbackFilename || `template-${templateId}`
  const cd = res.headers.get('Content-Disposition')
  if (cd) {
    const m = /filename\*?=(?:UTF-8''|)([^;\s]+)|filename="([^"]+)"/i.exec(cd)
    if (m) name = decodeURIComponent((m[1] || m[2] || '').trim()) || name
  }
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

/** Admin: replace template file and/or title (multipart PUT). */
export async function updateAdminTemplate(templateId, { title = '', file = null } = {}) {
  const token = getToken()
  const fd = new FormData()
  fd.append('title', title)
  if (file) fd.append('file', file)
  const res = await fetch(`${base}/forms/admin/templates/${templateId}`, {
    method: 'PUT',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: fd,
  })
  const text = await res.text()
  let data
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = null
  }
  if (!res.ok) {
    let msg = res.statusText
    if (typeof data === 'object' && data && data.detail) {
      msg = Array.isArray(data.detail)
        ? data.detail.map((d) => (typeof d === 'object' && d.msg ? d.msg : String(d))).join(', ')
        : String(data.detail)
    }
    throw new Error(msg || `HTTP ${res.status}`)
  }
  return data
}

export async function downloadSubmissionFile(submissionId, filename) {
  const token = getToken()
  const res = await fetch(`${base}/forms/submissions/${submissionId}/download`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) {
    const t = await res.text()
    throw new Error(t || res.statusText)
  }
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename || `submission-${submissionId}`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
