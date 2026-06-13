import Section from './Section.jsx'

// The ordered, plausible story of how a stranger chains the data (PLAN §4.9).
export default function AttackPath({ steps }) {
  return (
    <Section step="6" title="Attack path" hint="how the chain plays out">
      {steps.length === 0 ? (
        <div className="rounded-md border border-line bg-panel2 p-3 text-sm text-muted">
          No attack path — not enough fused signals to build a plausible chain.
        </div>
      ) : (
        <ol className="space-y-0">
          {steps.map((s, i) => (
            <li key={i} className="flex gap-3">
              <div className="flex flex-col items-center">
                <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full border border-danger/50 bg-danger/10 text-xs font-bold text-danger">
                  {i + 1}
                </span>
                {i < steps.length - 1 && <span className="my-1 w-px flex-1 bg-danger/30" />}
              </div>
              <p className="pb-3 pt-0.5 text-sm text-fg">{s}</p>
            </li>
          ))}
        </ol>
      )}
    </Section>
  )
}
