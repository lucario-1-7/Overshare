// Shown before the first analysis — sets the pitch and points at the two actions.
export default function EmptyState({ onLoadSample }) {
  return (
    <div className="panel grid place-items-center p-10 text-center">
      <div className="text-4xl">🛰️</div>
      <h2 className="mt-3 text-lg font-bold text-fg">See what a stranger sees</h2>
      <p className="mt-2 max-w-md text-sm text-muted">
        Drop a photo, caption, or username on the left. Overshare fuses the weak signals
        the way a real stranger would — and shows the exposure graph, risk scores, attack
        path, and one-click fixes.
      </p>
      <button className="btn-ghost mt-5" onClick={onLoadSample}>
        Load a sample report →
      </button>
    </div>
  )
}
