import { useRef, useState } from 'react'
import { analyzeProfile, footprint } from '../lib/api.js'
import Section from '../components/Section.jsx'

// Page 2 — the digital-footprint intelligence layer (backend/extras). Two tools:
//   • Identity footprint: an email and/or username → breach / presence / domain / gravatar,
//     scored into a Footprint Score + attacker effort + amplification + a time-to-exploit timeline.
//   • Multi-post pattern: several images → the core pipeline per post, aggregated by the
//     Pattern Engine into recurring entities, exposure consistency/trend, and insights.
export default function FootprintPage({ health }) {
  // State lives here and flows down via props — the two tools report results up
  // through onResult callbacks. (No module-level store: that mutated refs during
  // render and left stale setters when the tab unmounted mid-fetch.)
  const [fp, setFp] = useState(null)
  const [profile, setProfile] = useState(null)

  return (
    <div className="grid gap-4 lg:grid-cols-[380px_minmax(0,1fr)]">
      <div className="space-y-4 lg:sticky lg:top-6 lg:self-start">
        <IdentityTool health={health} onResult={setFp} />
        <MultiPostTool onResult={setProfile} />
        <p className="px-1 text-xs leading-relaxed text-muted/70">
          Image analysis stays local. Footprint lookups send <span className="text-fg">only the
          identifier you enter</span> (email / username) to free, key-free public sources — never an
          image. The report shows exactly what left the machine.
        </p>
      </div>
      <ResultsColumn fp={fp} profile={profile} />
    </div>
  )
}

function ResultsColumn({ fp, profile }) {
  if (!fp && !profile) {
    return (
      <div className="panel grid min-h-[280px] place-items-center p-8 text-center">
        <div>
          <div className="text-3xl">🛰️</div>
          <p className="mt-3 text-sm text-muted">
            Enter an email/username, or drop several posts, to map your digital footprint.
          </p>
          <p className="mt-1 text-xs text-muted/70">Tip: use “Try demo” for a rich, offline example.</p>
        </div>
      </div>
    )
  }
  return (
    <div className="space-y-4">
      {fp && <FootprintResult report={fp} />}
      {profile && <ProfileResult report={profile} />}
    </div>
  )
}

/* --------------------------------- tools ----------------------------------- */

function IdentityTool({ health, onResult }) {
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function scan(e, u) {
    setLoading(true)
    setError('')
    try {
      const rep = await footprint({ email: e ?? email.trim(), username: u ?? username.trim() })
      onResult(rep)
    } catch (err) {
      setError(String(err?.message || err))
    } finally {
      setLoading(false)
    }
  }

  function demo() {
    setEmail('demo@overshare.app')
    setUsername('torvalds')
    scan('demo@overshare.app', 'torvalds')
  }

  const can = !loading && (email.trim() || username.trim())
  return (
    <div className="panel p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="section-title">
          <span className="grid h-5 w-5 place-items-center rounded bg-ink text-[10px] font-bold text-neon ring-1 ring-line">
            A
          </span>
          <span>Identity footprint</span>
        </div>
        <ConnDot health={health} />
      </div>

      <label className="block text-xs text-muted">Email</label>
      <input
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="e.g. jane@company.com"
        className="mt-1 w-full rounded-md border border-line bg-ink p-2 text-sm outline-none focus:border-cyan"
      />
      <label className="mt-3 block text-xs text-muted">Username / handle</label>
      <input
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        placeholder="e.g. janedoe"
        className="mt-1 w-full rounded-md border border-line bg-ink p-2 text-sm outline-none focus:border-cyan"
      />

      <div className="mt-4 flex flex-wrap gap-2">
        <button className="btn-primary" disabled={!can} onClick={() => scan()}>
          {loading ? 'Scanning…' : 'Scan footprint'}
        </button>
        <button className="btn-ghost" disabled={loading} onClick={demo}>
          Try demo
        </button>
      </div>
      {error && (
        <div className="mt-3 rounded-md border border-danger/40 bg-danger/10 p-2 text-xs text-danger">
          {error}
          <div className="mt-1 text-danger/70">Is the backend running on :8077?</div>
        </div>
      )}
    </div>
  )
}

function MultiPostTool({ onResult }) {
  const inputRef = useRef(null)
  const [files, setFiles] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function run() {
    setLoading(true)
    setError('')
    try {
      const rep = await analyzeProfile(files)
      onResult(rep)
    } catch (err) {
      setError(String(err?.message || err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="panel p-4">
      <div className="section-title mb-3">
        <span className="grid h-5 w-5 place-items-center rounded bg-ink text-[10px] font-bold text-neon ring-1 ring-line">
          B
        </span>
        <span>Multi-post pattern</span>
        <span className="font-normal normal-case tracking-normal text-muted/70">· several photos</span>
      </div>

      <div
        onClick={() => inputRef.current?.click()}
        className="cursor-pointer rounded-lg border-2 border-dashed border-line p-5 text-center text-sm text-muted transition hover:border-muted"
      >
        <div className="text-2xl">🗂️</div>
        <div className="mt-1">{files.length ? `${files.length} image(s) selected` : 'Choose several posts'}</div>
        <div className="mt-1 text-xs text-muted/70">each runs the core pipeline, then we find the pattern</div>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        multiple
        hidden
        onChange={(e) => setFiles(Array.from(e.target.files || []))}
      />

      <div className="mt-4 flex flex-wrap gap-2">
        <button className="btn-primary" disabled={loading || !files.length} onClick={run}>
          {loading ? 'Analyzing…' : `Analyze ${files.length || ''} post${files.length === 1 ? '' : 's'}`.trim()}
        </button>
        {files.length > 0 && (
          <button
            className="btn-ghost"
            disabled={loading}
            onClick={() => {
              setFiles([])
              if (inputRef.current) inputRef.current.value = ''
            }}
          >
            Clear
          </button>
        )}
      </div>
      {error && (
        <div className="mt-3 rounded-md border border-danger/40 bg-danger/10 p-2 text-xs text-danger">{error}</div>
      )}
    </div>
  )
}

/* ------------------------------- rendering --------------------------------- */

// Higher footprint score = MORE exposed = worse. Red at the top, green when low.
function scoreColor(score) {
  if (score >= 70) return '#ff7b72' // danger
  if (score >= 40) return '#f0b72f' // amber
  return '#7ee787' // neon
}

function Bar({ label, score }) {
  const color = scoreColor(score)
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between text-sm">
        <span className="text-fg">{label}</span>
        <span className="tabular-nums text-sm font-bold" style={{ color }}>
          {score}
        </span>
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-ink ring-1 ring-line">
        <div
          className="h-full animate-grow rounded-full"
          style={{ '--w': `${Math.max(0, Math.min(100, score))}%`, background: color }}
        />
      </div>
    </div>
  )
}

const EFFORT_COLOR = { LOW: '#ff7b72', MEDIUM: '#f0b72f', HIGH: '#7ee787' }

function FootprintResult({ report }) {
  const score = report.footprintScore || 0
  const effort = report.attackerEffort || {}
  const amp = report.amplification || {}
  const sent = (report.meta && report.meta.sentToExternal) || []
  return (
    <Section title="Digital footprint" hint="from public, key-free sources">
      {/* headline */}
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="panel bg-ink/40 p-4 text-center">
          <div className="text-4xl font-bold tabular-nums" style={{ color: scoreColor(score) }}>
            {score}
          </div>
          <div className="mt-1 text-xs uppercase tracking-wider text-muted">Footprint score</div>
        </div>
        <div className="panel bg-ink/40 p-4 text-center">
          <div className="text-xl font-bold" style={{ color: EFFORT_COLOR[effort.level] || '#8b949e' }}>
            {effort.level || '—'}
          </div>
          <div className="mt-1 text-xs text-muted">attacker effort · {effort.eta || 'n/a'}</div>
          <div className="mt-1 text-[10px] text-muted/60">lower effort = higher exposure</div>
        </div>
        <div className="panel bg-ink/40 p-4 text-center">
          <div className="text-xl font-bold text-cyan tabular-nums">{amp.factor ?? '—'}×</div>
          <div className="mt-1 text-xs text-muted">inference amplification</div>
          <div className="mt-1 text-[10px] text-muted/60">
            {amp.rawInputs ?? 0} input → {amp.derivedInferences ?? 0} inferences
          </div>
        </div>
      </div>

      {/* categories */}
      {report.categories?.length > 0 && (
        <div className="mt-4 space-y-3">
          {report.categories.map((c) => (
            <Bar key={c.name} label={c.name} score={c.score} />
          ))}
        </div>
      )}

      {/* timeline */}
      {report.timeline?.length > 0 && (
        <div className="mt-5">
          <div className="section-title mb-2">Time to exploit</div>
          <ol className="relative space-y-2 border-l border-line pl-4">
            {report.timeline.map((s, i) => (
              <li key={i} className="relative">
                <span className="absolute -left-[21px] top-1 h-2 w-2 rounded-full bg-neon ring-2 ring-ink" />
                <span className="mr-2 inline-block w-12 text-xs font-bold text-cyan">{s.t}</span>
                <span className="text-sm text-fg">{s.label}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* raw signals */}
      {report.signals?.length > 0 && (
        <div className="mt-5">
          <div className="section-title mb-2">What was found ({report.signals.length})</div>
          <div className="space-y-2">
            {report.signals.map((s, i) => (
              <FootprintSignalRow key={i} sig={s} />
            ))}
          </div>
        </div>
      )}

      {/* privacy: what left the machine */}
      <div className="mt-5 rounded-md border border-line bg-ink/40 p-2.5 text-xs text-muted">
        <span className="text-fg">Sent to external sources:</span>{' '}
        {sent.length ? sent.join(' · ') : 'nothing'}
        <span className="text-muted/60"> — never an image; image analysis stays on-device.</span>
      </div>
    </Section>
  )
}

const SIG_LABEL = {
  breach_exposure: 'Breach',
  platform_presence: 'Account',
  email_domain: 'Email domain',
  organization: 'Organization',
  gravatar_profile: 'Gravatar',
  github_profile: 'GitHub',
  location: 'Location',
}

function FootprintSignalRow({ sig }) {
  const d = sig.detail || {}
  const url = d.url
  const names = Array.isArray(d.names) ? d.names : null
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-md border border-line bg-panel2 px-2.5 py-1.5 text-sm">
      <span className="chip border-cyan/40 text-cyan">{SIG_LABEL[sig.type] || sig.type}</span>
      {url ? (
        <a href={url} target="_blank" rel="noreferrer" className="text-fg underline decoration-line hover:text-cyan">
          {sig.value}
        </a>
      ) : (
        <span className="text-fg">{sig.value}</span>
      )}
      {names && <span className="text-xs text-muted/80">{names.slice(0, 8).join(', ')}{names.length > 8 ? '…' : ''}</span>}
      <span className="ml-auto text-[10px] uppercase tracking-wider text-muted/60">{sig.source}</span>
    </div>
  )
}

const TREND_COLOR = { increasing: '#ff7b72', decreasing: '#7ee787', stable: '#79c0ff', 'n/a': '#8b949e' }

function ProfileResult({ report }) {
  // Defaults: the extras responses aren't run through normalizeReport, so guard fields.
  const scores = report.perPostScores || []
  const max = Math.max(1, ...scores)
  const footprintScore = report.footprintScore ?? 0
  const consistency = report.exposureConsistency ?? 0
  const trend = report.exposureTrend || 'n/a'
  const totalPosts = report.totalPosts ?? 0
  return (
    <Section title="Multi-post pattern" hint={`${totalPosts} post(s)`}>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Footprint" value={footprintScore} color={scoreColor(footprintScore)} />
        <Stat label="Exposure consistency" value={`${consistency}%`} color={scoreColor(consistency)} />
        <Stat label="Trend" value={trend} color={TREND_COLOR[trend] || '#8b949e'} small />
        <Stat label="Posts" value={totalPosts} color="#79c0ff" />
      </div>

      {/* per-post exposure sparkline */}
      {scores.length > 0 && (
        <div className="mt-4">
          <div className="section-title mb-2">Per-post exposure</div>
          <div className="flex items-end gap-1.5" style={{ height: 64 }}>
            {scores.map((s, i) => (
              <div
                key={i}
                title={`Post ${i + 1}: ${s}`}
                className="flex-1 rounded-t"
                style={{ height: `${(s / max) * 100}%`, minHeight: 3, background: scoreColor(s) }}
              />
            ))}
          </div>
        </div>
      )}

      {/* recurring entities */}
      {report.recurringEntities?.length > 0 && (
        <div className="mt-5">
          <div className="section-title mb-2">Recurring across posts</div>
          <div className="space-y-1.5">
            {report.recurringEntities.map((e, i) => (
              <div key={i} className="flex items-center gap-2 text-sm">
                <span className="chip border-amber/40 text-amber">{e.type}</span>
                <span className="text-fg">{e.value}</span>
                <span className="ml-auto text-xs text-muted">{e.posts}/{e.totalPosts} posts</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* insights */}
      {report.insights?.length > 0 && (
        <div className="mt-5">
          <div className="section-title mb-2">Insights</div>
          <div className="space-y-2">
            {report.insights.map((ins, i) => (
              <div key={i} className="rounded-md border border-line bg-panel2 p-2.5">
                <div className="text-sm text-fg">{ins.label}</div>
                <div className="mt-0.5 text-xs text-muted/80">{ins.evidence}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* signal frequency */}
      {report.signalFrequency && Object.keys(report.signalFrequency).length > 0 && (
        <div className="mt-5">
          <div className="section-title mb-2">Signal frequency</div>
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(report.signalFrequency).map(([t, n]) => (
              <span key={t} className="chip border-line text-muted">
                {t} <span className="text-fg">·{n}</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </Section>
  )
}

function Stat({ label, value, color, small }) {
  return (
    <div className="panel bg-ink/40 p-3 text-center">
      <div className={`font-bold tabular-nums ${small ? 'text-base' : 'text-2xl'}`} style={{ color }}>
        {value}
      </div>
      <div className="mt-1 text-[11px] leading-tight text-muted">{label}</div>
    </div>
  )
}

function ConnDot({ health }) {
  const ok = health?.status === 'ok'
  return (
    <span className="flex items-center gap-1.5 text-[10px] text-muted" title={ok ? 'backend ok' : 'backend offline'}>
      <span
        className="inline-block h-2 w-2 rounded-full"
        style={{ background: ok ? '#7ee787' : '#8b949e', boxShadow: ok ? '0 0 8px #7ee787' : 'none' }}
      />
      {ok ? 'online' : 'offline'}
    </span>
  )
}
