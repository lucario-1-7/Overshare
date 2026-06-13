import { useRef, useState } from 'react'

// Upload panel: drag/drop an image, optional caption + username, Analyze button,
// and a "Load sample" shortcut so the full experience works with no backend.
export default function Uploader({ onAnalyze, onLoadSample, onClear, loading, error, health }) {
  const inputRef = useRef(null)
  const [file, setFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState(null)
  const [text, setText] = useState('')
  const [username, setUsername] = useState('')
  const [hot, setHot] = useState(false)

  function pick(f) {
    if (!f) return
    setFile(f)
    setPreviewUrl(URL.createObjectURL(f))
  }

  function reset() {
    setFile(null)
    setPreviewUrl(null)
    setText('')
    setUsername('')
    if (inputRef.current) inputRef.current.value = ''
    onClear?.()
  }

  const canAnalyze = !loading && (file || text.trim() || username.trim())

  return (
    <div className="panel p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="section-title">
          <span className="grid h-5 w-5 place-items-center rounded bg-ink text-[10px] font-bold text-neon ring-1 ring-line">
            1
          </span>
          <span>Upload</span>
        </div>
        <ConnDot health={health} />
      </div>

      <div
        onClick={() => inputRef.current?.click()}
        onDragEnter={(e) => {
          e.preventDefault()
          setHot(true)
        }}
        onDragOver={(e) => e.preventDefault()}
        onDragLeave={(e) => {
          e.preventDefault()
          setHot(false)
        }}
        onDrop={(e) => {
          e.preventDefault()
          setHot(false)
          pick(e.dataTransfer.files?.[0])
        }}
        className={`cursor-pointer rounded-lg border-2 border-dashed p-6 text-center text-sm transition ${
          hot ? 'border-neon bg-neon/5 text-neon' : 'border-line text-muted hover:border-muted'
        }`}
      >
        {previewUrl ? (
          <img src={previewUrl} alt="preview" className="mx-auto max-h-44 rounded-md" />
        ) : (
          <>
            <div className="text-2xl">📷</div>
            <div className="mt-1">Drop an image, or click to choose</div>
            <div className="mt-1 text-xs text-muted/70">photo · screenshot · selfie with a badge</div>
          </>
        )}
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        hidden
        onChange={(e) => pick(e.target.files?.[0])}
      />
      {file && (
        <div className="mt-1.5 truncate text-xs text-muted">
          {file.name} · {Math.round(file.size / 1024)} KB
        </div>
      )}

      <label className="mt-4 block text-xs text-muted">Caption / text (optional)</label>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="e.g. lunch near MG Road with the team"
        className="mt-1 min-h-[56px] w-full resize-y rounded-md border border-line bg-ink p-2 text-sm outline-none focus:border-cyan"
      />

      <label className="mt-3 block text-xs text-muted">Username / email (optional)</label>
      <input
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        placeholder="e.g. janedoe"
        className="mt-1 w-full rounded-md border border-line bg-ink p-2 text-sm outline-none focus:border-cyan"
      />

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          className="btn-primary"
          disabled={!canAnalyze}
          onClick={() => onAnalyze({ file, text: text.trim(), username: username.trim() })}
        >
          {loading ? 'Analyzing…' : 'Analyze'}
        </button>
        <button className="btn-ghost" disabled={loading} onClick={onLoadSample}>
          Load sample
        </button>
        <button className="btn-ghost" disabled={loading} onClick={reset}>
          Clear
        </button>
      </div>

      {error && (
        <div className="mt-3 rounded-md border border-danger/40 bg-danger/10 p-2 text-xs text-danger">
          {error}
          <div className="mt-1 text-danger/70">Is the backend running on :8077? (or use “Load sample”.)</div>
        </div>
      )}
    </div>
  )
}

function ConnDot({ health }) {
  const ok = health?.status === 'ok'
  const title = ok
    ? `backend ok · device=${health.device}${health.cuda_available ? ' (GPU)' : ''} · models=${(health.models || []).join(',') || 'none'}`
    : 'backend not reachable'
  return (
    <span className="flex items-center gap-1.5 text-[10px] text-muted" title={title}>
      <span
        className="inline-block h-2 w-2 rounded-full"
        style={{ background: ok ? '#7ee787' : '#8b949e', boxShadow: ok ? '0 0 8px #7ee787' : 'none' }}
      />
      {ok ? (health.cuda_available ? 'GPU' : 'CPU') : 'offline'}
    </span>
  )
}
