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
