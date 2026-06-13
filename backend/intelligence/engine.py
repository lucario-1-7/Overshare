"""Intelligence aggregator (PLAN §4.7–§4.10) — the seam assemble.py calls.

This file is the STABLE integration point: assemble.py calls build_intelligence(signals)
and never needs to change. The Phase 4 person only fills in the four sub-modules
(graph.py / risk.py / attack.py / fix.py); each runs independently over signals[].

Returns a plain dict whose keys map 1:1 onto the Report fields. Each sub-engine is
wrapped so one failing engine degrades to its empty default instead of failing the
whole request (reliability first).
"""
from __future__ import annotations

from typing import Any, Dict, List

from backend.contracts.report import Graph, Risks
from backend.contracts.signal import Signal

from .attack import build_attack_path
from .fix import suggest_fixes
from .graph import build_graph
from .risk import score_risks


def build_intelligence(signals: List[Signal]) -> Dict[str, Any]:
    """Run all four engines over signals[]; return {graph, risks, attackPath, fixes}."""

    def _safe(fn, default):
        try:
            return fn(signals)
        except Exception as e:  # noqa: BLE001 — one bad engine must not 500 the request
            print(f"[intelligence] {fn.__module__} skipped ({type(e).__name__}: {e}).")
            return default

    return {
        "graph": _safe(build_graph, Graph()),
        "risks": _safe(score_risks, Risks()),
        "attackPath": _safe(build_attack_path, []),
        "fixes": _safe(suggest_fixes, []),
    }
