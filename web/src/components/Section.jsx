// A consistent titled section. `step` renders the little arcade index badge so the
// report reads as the fixed, ordered sequence the plan specifies (PLAN §4.1).
export default function Section({ step, title, hint, right, children }) {
  return (
    <section className="panel animate-fadein p-4">
      <header className="mb-3 flex items-center justify-between gap-3">
        <div className="section-title">
          {step != null && (
            <span className="grid h-5 w-5 place-items-center rounded bg-ink text-[10px] font-bold text-neon ring-1 ring-line">
              {step}
            </span>
          )}
          <span>{title}</span>
          {hint && <span className="font-normal normal-case tracking-normal text-muted/70">· {hint}</span>}
        </div>
        {right}
      </header>
      {children}
    </section>
  )
}
