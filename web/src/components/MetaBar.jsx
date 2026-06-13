// The privacy differentiator, made loud (PLAN §7 / Slide 6 "DATABASE = None, by design").
export default function MetaBar({ meta }) {
  const models = meta.modelsRun || []
  return (
    <div className="panel flex flex-wrap items-center gap-x-4 gap-y-2 p-3 text-xs">
      <Flag ok={meta.processedLocally} label="Processed on-device" />
      <Flag ok={!meta.stored} label="Nothing stored" />
      <span className="text-muted">
        models:{' '}
        {models.length ? (
          <span className="text-fg">{models.join(' · ')}</span>
        ) : (
          <span className="text-muted/70">none</span>
        )}
      </span>
    </div>
  )
}

function Flag({ ok, label }) {
  return (
    <span className="flex items-center gap-1.5">
      <span style={{ color: ok ? '#7ee787' : '#ff7b72' }}>{ok ? '✓' : '✕'}</span>
      <span className={ok ? 'text-fg' : 'text-danger'}>{label}</span>
    </span>
  )
}
