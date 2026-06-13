import { useEffect, useState } from 'react'
import { fetchHealth } from './lib/api.js'
import ScannerPage from './pages/ScannerPage.jsx'
import FootprintPage from './pages/FootprintPage.jsx'

const TABS = [
  { id: 'scanner', label: 'Image / Text Scanner', icon: '🔎' },
  { id: 'footprint', label: 'Digital Footprint', icon: '🛰️' },
]

export default function App() {
  const [view, setView] = useState('scanner')
  const [health, setHealth] = useState(null)

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch(() => setHealth(null))
  }, [])

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <Header view={view} setView={setView} />
      <div className="mt-6">
        {view === 'scanner' ? <ScannerPage health={health} /> : <FootprintPage health={health} />}
      </div>
      <Footer />
    </div>
  )
}

function Header({ view, setView }) {
  return (
    <header className="space-y-4">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-[0.18em] text-neon">🛰️ OVERSHARE</h1>
          <p className="mt-1 text-sm text-muted">
            What a stranger could infer about you — across a single post and your whole digital footprint.
          </p>
        </div>
        <span className="chip border-neon/40 text-neon">on-device · nothing leaves this machine</span>
      </div>

      {/* page nav */}
      <nav className="flex gap-1 rounded-lg border border-line bg-panel p-1">
        {TABS.map((t) => {
          const active = view === t.id
          return (
            <button
              key={t.id}
              onClick={() => setView(t.id)}
              className={`flex-1 rounded-md px-3 py-2 text-sm font-semibold transition ${
                active ? 'bg-ink text-neon ring-1 ring-neon/40' : 'text-muted hover:text-fg'
              }`}
            >
              <span className="mr-1.5">{t.icon}</span>
              {t.label}
            </button>
          )
        })}
      </nav>
    </header>
  )
}

function Footer() {
  return (
    <footer className="mt-8 border-t border-line pt-4 text-center text-xs text-muted/70">
      Overshare · ARCNIGHT 2026 · CyberTech — all inference runs locally, no external model API.
    </footer>
  )
}
