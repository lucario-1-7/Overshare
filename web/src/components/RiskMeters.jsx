import Section from './Section.jsx'
import { riskBand } from '../lib/report.js'

// Deterministic risk scores as meters (PLAN §4.8). Same input → same score, so the
// demo is repeatable. The band label makes the number legible at a glance.
const CATS = [
  { key: 'doxxing', label: 'Doxxing' },
  { key: 'stalking', label: 'Stalking' },
  { key: 'phishing', label: 'Phishing' },
]

export default function RiskMeters({ risks }) {
  const allZero = CATS.every((c) => !risks[c.key])
  return (
    <Section step="5" title="Risk scores" hint="0–100 · deterministic">
      <div className="space-y-4">
        {CATS.map((c) => (
          <Meter key={c.key} label={c.label} score={risks[c.key] || 0} />
        ))}
      </div>
      {allZero && (
        <div className="mt-3 text-xs text-muted/70">
          Scores stay at 0 until the intelligence layer scores the signal set (Phase 4).
        </div>
      )}
    </Section>
  )
}

function Meter({ label, score }) {
  const band = riskBand(score)
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between text-sm">
        <span className="text-fg">{label}</span>
        <span className="tabular-nums">
          <span className="text-lg font-bold" style={{ color: band.color }}>
            {score}
          </span>
          <span className="ml-2 text-xs uppercase tracking-wider" style={{ color: band.color }}>
            {band.label}
          </span>
        </span>
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-ink ring-1 ring-line">
        <div
          className="h-full animate-grow rounded-full"
          style={{ '--w': `${Math.max(0, Math.min(100, score))}%`, background: band.color }}
        />
      </div>
    </div>
  )
}
