import { useMemo } from 'react'
import ReactFlow, { Background, Controls, MarkerType } from 'reactflow'
import 'reactflow/dist/style.css'
import Section from './Section.jsx'
import { nodeStyle, isFusionEdge } from '../lib/report.js'

// The named innovation (PLAN §4.7): a You-centred map of everything exposed, with
// fusion edges highlighting combined risk (GPS + bedroom → "Home locatable").
// Backend nodes carry no coordinates, so we lay them out radially here and let
// react-flow do the rendering/pan/zoom (the plan says: don't hand-roll the graph).
function buildLayout(graph) {
  const nodes = graph.nodes || []
  const edges = graph.edges || []
  const center = nodes.find((n) => n.type === 'user' || n.id === 'user') || nodes[0]
  const others = nodes.filter((n) => n !== center)
  const fusion = others.filter((n) => n.type === 'fusion')
  const ring = others.filter((n) => n.type !== 'fusion')

  const pos = {}
  if (center) pos[center.id] = { x: 0, y: 0 }
  const place = (arr, radius, offset = 0) =>
    arr.forEach((n, i) => {
      const a = (i / Math.max(arr.length, 1)) * 2 * Math.PI - Math.PI / 2 + offset
      pos[n.id] = { x: Math.cos(a) * radius, y: Math.sin(a) * radius }
    })
  place(ring, 260)
  place(fusion, 470, 0.35)

  const nodeTypeById = Object.fromEntries(nodes.map((n) => [n.id, n.type]))

  const rfNodes = nodes.map((n) => {
    const s = nodeStyle(n.type)
    const isUser = n === center
    return {
      id: n.id,
      position: pos[n.id] || { x: 0, y: 0 },
      data: { label: n.label },
      draggable: true,
      style: {
        background: s.bg,
        border: `${isUser ? 2 : 1}px solid ${s.border}`,
        color: s.color,
        borderRadius: 10,
        padding: '8px 12px',
        fontSize: 12,
        fontWeight: 600,
        width: 'auto',
        maxWidth: 190,
        textAlign: 'center',
        boxShadow: isUser ? '0 0 24px -6px rgba(126,231,135,0.6)' : 'none',
      },
    }
  })

  const rfEdges = edges.map((e, i) => {
    const fused = isFusionEdge(e, nodeTypeById)
    const stroke = fused ? '#ff7b72' : '#3b4350'
    return {
      id: `e${i}`,
      source: e.source,
      target: e.target,
      label: e.label,
      animated: fused,
      style: { stroke, strokeWidth: fused ? 2.2 : 1.4 },
      labelStyle: { fill: fused ? '#ff7b72' : '#8b949e', fontSize: 10, fontFamily: 'monospace' },
      labelBgStyle: { fill: '#0b0f17', opacity: 0.85 },
      labelBgPadding: [4, 2],
      markerEnd: { type: MarkerType.ArrowClosed, color: stroke, width: 16, height: 16 },
    }
  })

  return { rfNodes, rfEdges }
}

export default function ExposureGraph({ graph }) {
  const { rfNodes, rfEdges } = useMemo(() => buildLayout(graph), [graph])
  const hasFusion = (graph.nodes || []).some((n) => n.type === 'fusion')

  return (
    <Section
      step="4"
      title="Exposure graph"
      hint="how a stranger fuses the signals"
      right={
        hasFusion ? (
          <span className="chip border-danger/40 text-danger">
            <span className="inline-block h-2 w-2 rounded-full" style={{ background: '#ff7b72' }} />
            fused risk
          </span>
        ) : null
      }
    >
      {rfNodes.length === 0 ? (
        <div className="rounded-md border border-line bg-panel2 p-3 text-sm text-muted">
          No exposure graph yet — it builds once signals are present (intelligence layer, Phase 4).
        </div>
      ) : (
        <div className="h-[460px] overflow-hidden rounded-lg border border-line bg-panel2">
          <ReactFlow
            nodes={rfNodes}
            edges={rfEdges}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            minZoom={0.2}
            proOptions={{ hideAttribution: true }}
            nodesConnectable={false}
            elementsSelectable={false}
          >
            <Background color="#1b2230" gap={20} />
            <Controls showInteractive={false} />
          </ReactFlow>
        </div>
      )}
    </Section>
  )
}
