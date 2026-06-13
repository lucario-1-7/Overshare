// The frozen contract, mirrored from backend/contracts/{signal,report}.py.
// The UI is "dumb": it only ever reads a Report. Nothing here talks to a model.
//
// @typedef {Object} Evidence
// @property {number[]=} bbox   // [x, y, w, h]
// @property {string=}   text
// @property {*=}        raw
//
// @typedef {Object} Signal
// @property {string} type        // gps|face|employer|location|person_name|email|phone|username|home_indicator|device|timestamp|screen_text|document|person|address
// @property {string} value
// @property {string} source      // exif|retinaface|paddleocr|easyocr|yolo|presidio|footprint
// @property {number} confidence  // 0..1
// @property {Evidence|null=} evidence
//
// @typedef {Object} GraphNode  @property {string} id @property {string} label @property {string=} type @property {Object=} data
// @typedef {Object} GraphEdge  @property {string} source @property {string} target @property {string=} label
// @typedef {Object} Graph      @property {GraphNode[]} nodes @property {GraphEdge[]} edges
// @typedef {Object} Risks      @property {number} doxxing @property {number} stalking @property {number} phishing
// @typedef {Object} Fix        @property {string} issue @property {string} action @property {boolean} oneClick
// @typedef {Object} Meta       @property {boolean} processedLocally @property {boolean} stored @property {string[]} modelsRun
//
// @typedef {Object} Report
// @property {string|null} annotatedImage
// @property {Signal[]} signals
// @property {Graph} graph
// @property {Risks} risks
// @property {string[]} attackPath
// @property {Fix[]} fixes
// @property {string|null} explanation
// @property {Meta} meta

/** Per-signal-type presentation: icon + readable label + accent colour. */
export const SIGNAL_META = {
  gps: { icon: '📍', label: 'GPS', color: '#ff7b72' },
  device: { icon: '📱', label: 'Device', color: '#79c0ff' },
  timestamp: { icon: '🕒', label: 'Timestamp', color: '#79c0ff' },
  face: { icon: '🙂', label: 'Face', color: '#f0b72f' },
  person: { icon: '🧍', label: 'Person', color: '#f0b72f' },
  home_indicator: { icon: '🛋️', label: 'Home indicator', color: '#ff7b72' },
  document: { icon: '📄', label: 'Document', color: '#a5d6ff' },
  screen_text: { icon: '🔡', label: 'Screen text', color: '#a5d6ff' },
  employer: { icon: '🏢', label: 'Employer', color: '#d2a8ff' },
  person_name: { icon: '🪪', label: 'Name', color: '#d2a8ff' },
  email: { icon: '✉️', label: 'Email', color: '#ffa657' },
  phone: { icon: '☎️', label: 'Phone', color: '#ffa657' },
  location: { icon: '🗺️', label: 'Location', color: '#7ee787' },
  address: { icon: '🏠', label: 'Address', color: '#ff7b72' },
  username: { icon: '🔗', label: 'Username', color: '#7ee787' },
}

export function signalMeta(type) {
  return SIGNAL_META[type] || { icon: '•', label: type, color: '#8b949e' }
}

/** Per-source colour for chip borders (which model produced the signal). */
export const SOURCE_COLOR = {
  exif: '#79c0ff',
  yolo: '#f0b72f',
  retinaface: '#f0b72f',
  paddleocr: '#a5d6ff',
  easyocr: '#a5d6ff',
  presidio: '#d2a8ff',
  footprint: '#7ee787',
}

/** Graph node styling by node.type. `user` is the centre; `fusion` is escalated risk. */
export function nodeStyle(type) {
  if (type === 'user') return { bg: '#0b2a1a', border: '#7ee787', color: '#7ee787' }
  if (type === 'fusion') return { bg: '#2a0f0f', border: '#ff7b72', color: '#ff7b72' }
  const m = SIGNAL_META[type]
  if (m) return { bg: '#11161f', border: m.color, color: m.color }
  return { bg: '#11161f', border: '#30363d', color: '#e6edf3' }
}

/** An edge is a "fused risk" edge if it touches a fusion node or its label says so. */
export function isFusionEdge(edge, nodeTypeById) {
  const t = (edge.label || '').toLowerCase()
  return (
    nodeTypeById[edge.source] === 'fusion' ||
    nodeTypeById[edge.target] === 'fusion' ||
    t.includes('fus') ||
    t.includes('+')
  )
}

/** Risk score (0..100) → qualitative band + colour. */
export function riskBand(score) {
  const s = Number(score) || 0
  if (s >= 85) return { label: 'Critical', color: '#ff7b72' }
  if (s >= 67) return { label: 'High', color: '#ffa657' }
  if (s >= 34) return { label: 'Elevated', color: '#f0b72f' }
  if (s > 0) return { label: 'Low', color: '#7ee787' }
  return { label: 'None', color: '#8b949e' }
}

/** A normalized, fully-defaulted Report so components never crash on a partial payload. */
export function normalizeReport(r) {
  r = r || {}
  return {
    annotatedImage: r.annotatedImage ?? null,
    signals: Array.isArray(r.signals) ? r.signals : [],
    graph: {
      nodes: r.graph?.nodes ?? [],
      edges: r.graph?.edges ?? [],
    },
    risks: {
      doxxing: r.risks?.doxxing ?? 0,
      stalking: r.risks?.stalking ?? 0,
      phishing: r.risks?.phishing ?? 0,
    },
    attackPath: Array.isArray(r.attackPath) ? r.attackPath : [],
    fixes: Array.isArray(r.fixes) ? r.fixes : [],
    explanation: r.explanation ?? null,
    meta: {
      processedLocally: r.meta?.processedLocally ?? true,
      stored: r.meta?.stored ?? false,
      modelsRun: r.meta?.modelsRun ?? [],
    },
  }
}
