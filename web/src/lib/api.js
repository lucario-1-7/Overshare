// Thin client over the three backend routes. URLs are relative so the Vite dev
// proxy (vite.config.js) forwards them to the FastAPI backend, and the same build
// works unchanged when served from the backend's origin behind the tunnel.

async function asJson(res) {
  if (!res.ok) {
    let detail = ''
    try {
      detail = (await res.json()).detail || ''
    } catch {
      /* ignore */
    }
    throw new Error(`HTTP ${res.status}${detail ? ` — ${detail}` : ''}`)
  }
  return res.json()
}

/** POST an image (multipart) plus optional caption/username → Report. */
export async function analyze({ file, text, username }) {
  if (file) {
    const fd = new FormData()
    fd.append('file', file)
    if (text) fd.append('text', text)
    if (username) fd.append('username', username)
    return asJson(await fetch('/analyze', { method: 'POST', body: fd }))
  }
  return asJson(
    await fetch('/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text || null, username: username || null }),
    }),
  )
}

/** GET the fully-populated golden Report from the backend. */
export async function fetchSampleReport() {
  return asJson(await fetch('/sample-report'))
}

/** GET backend health (used for the connection indicator). */
export async function fetchHealth() {
  return asJson(await fetch('/health'))
}
