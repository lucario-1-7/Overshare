import { useState } from 'react'
import Section from './Section.jsx'

// Remediations (PLAN §4.10). The one-click EXIF strip is the satisfying closer:
// we re-encode the uploaded image via a canvas, which drops ALL metadata (incl.
// GPS), and hand back a clean download — done entirely on-device, no upload.
export default function Fixes({ fixes, uploadedFile }) {
  return (
    <Section step="7" title="Fixes" hint="undo the exposure">
      {fixes.length === 0 ? (
        <div className="rounded-md border border-line bg-panel2 p-3 text-sm text-muted">
          Nothing to fix.
        </div>
      ) : (
        <div className="grid gap-2 sm:grid-cols-2">
          {fixes.map((f, i) => (
            <FixCard key={i} fix={f} uploadedFile={uploadedFile} />
          ))}
        </div>
      )}
    </Section>
  )
}

function FixCard({ fix, uploadedFile }) {
  const [done, setDone] = useState(false)
  const [err, setErr] = useState('')

  async function strip() {
    setErr('')
    try {
      await stripExifAndDownload(uploadedFile)
      setDone(true)
    } catch (e) {
      setErr(String(e?.message || e))
    }
  }

  return (
    <div className="flex flex-col justify-between rounded-lg border border-line bg-panel2 p-3">
      <div>
        <div className="text-sm font-semibold text-fg">{fix.issue}</div>
        <div className="mt-0.5 text-xs text-muted">{fix.action}</div>
      </div>
      <div className="mt-2.5">
        {fix.oneClick ? (
          uploadedFile ? (
            <button className="btn-primary w-full py-1.5 text-xs" onClick={strip} disabled={done}>
              {done ? '✓ Clean image downloaded' : '⚡ Strip & download clean'}
            </button>
          ) : (
            <span className="chip border-line text-muted/70" title="Upload an image to use this fix">
              one-click · needs an upload
            </span>
          )
        ) : (
          <span className="chip border-line text-muted">manual</span>
        )}
        {err && <div className="mt-1 text-xs text-danger">{err}</div>}
      </div>
    </div>
  )
}

// Re-draw the image onto a canvas and re-encode it: canvas output carries no EXIF,
// so GPS/device/timestamp are gone. Triggers a download of the metadata-free copy.
function stripExifAndDownload(file) {
  return new Promise((resolve, reject) => {
    if (!file) return reject(new Error('no image to strip'))
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      try {
        const canvas = document.createElement('canvas')
        canvas.width = img.naturalWidth
        canvas.height = img.naturalHeight
        canvas.getContext('2d').drawImage(img, 0, 0)
        canvas.toBlob(
          (blob) => {
            URL.revokeObjectURL(url)
            if (!blob) return reject(new Error('encode failed'))
            const a = document.createElement('a')
            const dl = URL.createObjectURL(blob)
            a.href = dl
            a.download = cleanName(file.name)
            document.body.appendChild(a)
            a.click()
            a.remove()
            setTimeout(() => URL.revokeObjectURL(dl), 1000)
            resolve()
          },
          'image/jpeg',
          0.95,
        )
      } catch (e) {
        reject(e)
      }
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('could not load image'))
    }
    img.src = url
  })
}

function cleanName(name) {
  const base = (name || 'image').replace(/\.[^.]+$/, '')
  return `${base}-clean.jpg`
}
