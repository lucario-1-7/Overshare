import Section from './Section.jsx'
import { signalMeta, SOURCE_COLOR } from '../lib/report.js'

// Detected signals as chips, grouped by the model that produced them so the
// "5 models doing real inference" story is visible at a glance (PLAN §4.4).
export default function SignalChips({ signals }) {
  const groups = {}
  for (const s of signals) (groups[s.source] ||= []).push(s)
  const sources = Object.keys(groups)

  return (
    <Section step="3" title="Detected signals" hint={`${signals.length} found`}>
      {signals.length === 0 ? (
        <Empty>No signals detected — nothing a stranger could pull from this. Clean.</Empty>
      ) : (
        <div className="space-y-3">
          {sources.map((src) => (
            <div key={src}>
              <div className="mb-1.5 text-[10px] uppercase tracking-widest text-muted">{src}</div>
              <div className="flex flex-wrap gap-1.5">
                {groups[src].map((s, i) => (
                  <Chip key={i} signal={s} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </Section>
  )
}

function Chip({ signal }) {
  const m = signalMeta(signal.type)
  const border = SOURCE_COLOR[signal.source] || '#30363d'
  const pct = Math.round((signal.confidence ?? 0) * 100)
  const title = signal.evidence?.text || signal.value
  return (
    <span
      className="chip bg-panel2"
      style={{ borderColor: `${border}66`, color: '#e6edf3' }}
      title={`${m.label} · ${pct}% confidence${title ? `\n${title}` : ''}`}
    >
      <span>{m.icon}</span>
      <span className="font-semibold" style={{ color: m.color }}>
        {m.label}
      </span>
      <span className="max-w-[180px] truncate text-muted">{signal.value}</span>
      <span className="text-[10px] text-muted/70">{pct}%</span>
    </span>
  )
}

function Empty({ children }) {
  return <div className="rounded-md border border-line bg-panel2 p-3 text-sm text-muted">{children}</div>
}
