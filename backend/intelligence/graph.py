"""Exposure Graph builder (PLAN §4.7) — PHASE 4 LANE.  [STUB — fill this in]

THE PROJECT'S NAMED INNOVATION. Turn the set of present signal TYPES into a graph
centred on a `User` node, for react-flow on the frontend (Phase 5).

CONTRACT (do not change the signature; engine.py already calls it):
    build_graph(signals) -> Graph        # from backend.contracts.report

Logic (PLAN §4.7):
  - one central node id="user", type="user", label="You"
  - each present signal type becomes a child node (Face Visible, Employer Known,
    Location Known, Username Known, Home Indicator, ...), edge user->node
    label="is exposed via"
  - FUSION edges for combined risk, e.g. gps + home_indicator -> a "Home locatable"
    node/edge; these highlight that fused signals are worse than the sum.

GraphNode(id, label, type?, data?)  /  GraphEdge(source, target, label?)
Keep node ids stable + descriptive (the frontend keys off them). Deterministic:
same signal set -> same graph, every time.
"""
from __future__ import annotations

from typing import List

from backend.contracts.report import Graph
from backend.contracts.signal import Signal


def build_graph(signals: List[Signal]) -> Graph:
    """PHASE 4: build the exposure graph from the distinct signal types.
    Stub returns an empty graph (current behavior)."""
    # TODO(phase4): build the User-centred node/edge set + fusion edges.
    return Graph()
