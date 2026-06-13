import { useState } from 'react'
import { analyze } from '../lib/api.js'
import { normalizeReport } from '../lib/report.js'
import { SAMPLE_REPORT } from '../lib/sampleReport.js'

import Uploader from '../components/Uploader.jsx'
import MetaBar from '../components/MetaBar.jsx'
import AnnotatedImage from '../components/AnnotatedImage.jsx'
import SignalChips from '../components/SignalChips.jsx'
import ExposureGraph from '../components/ExposureGraph.jsx'
import RiskMeters from '../components/RiskMeters.jsx'
import AttackPath from '../components/AttackPath.jsx'
import Fixes from '../components/Fixes.jsx'
import Explanation from '../components/Explanation.jsx'
import EmptyState from '../components/EmptyState.jsx'

// Page 1 — the single-input scanner: image / caption / username -> the full Report
// (annotated image, signals, exposure graph, risk, attack path, fixes, explanation).
export default function ScannerPage({ health }) {
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [uploadedFile, setUploadedFile] = useState(null) // kept for the one-click EXIF strip
  const [originalUrl, setOriginalUrl] = useState(null)

  async function runAnalyze({ file, text, username }) {
    setLoading(true)
    setError('')
    setUploadedFile(file || null)
    setOriginalUrl(file ? URL.createObjectURL(file) : null)
    try {
      const raw = await analyze({ file, text, username })
      setReport(normalizeReport(raw))
    } catch (e) {
      setError(String(e?.message || e))
    } finally {
      setLoading(false)
    }
  }

  function loadSample() {
    setError('')
    setUploadedFile(null)
    setOriginalUrl(null)
    setReport(normalizeReport(SAMPLE_REPORT))
  }

  function clearAll() {
    setReport(null)
    setError('')
    setUploadedFile(null)
    setOriginalUrl(null)
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[380px_minmax(0,1fr)]">
      {/* Left rail */}
      <div className="space-y-4 lg:sticky lg:top-6 lg:self-start">
        <Uploader
          onAnalyze={runAnalyze}
          onLoadSample={loadSample}
          onClear={clearAll}
          loading={loading}
          error={error}
          health={health}
        />
        {report && <MetaBar meta={report.meta} />}
      </div>

      {/* Report */}
      <div className="space-y-4">
        {!report ? (
          <EmptyState onLoadSample={loadSample} />
        ) : (
          <>
            <AnnotatedImage annotatedImage={report.annotatedImage} fallbackUrl={originalUrl} />
            <SignalChips signals={report.signals} />
            <ExposureGraph graph={report.graph} />
            <div className="grid gap-4 md:grid-cols-2">
              <RiskMeters risks={report.risks} />
              <AttackPath steps={report.attackPath} />
            </div>
            <Fixes fixes={report.fixes} uploadedFile={uploadedFile} />
            <Explanation text={report.explanation} />
          </>
        )}
      </div>
    </div>
  )
}
