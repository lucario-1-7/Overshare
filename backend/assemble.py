"""Report assembly (PLAN §3 step 11, §4.12).

Takes the populated signals[] and builds a schema-valid Report. The graph / risks /
attackPath / fixes come from the Phase 4 intelligence layer via build_intelligence();
until those engines are filled in they return valid-but-empty defaults, so this file
is the STABLE seam — the Phase 4 person edits backend/intelligence/, never here.
"""
from __future__ import annotations

from typing import List, Optional

from backend.contracts.report import Meta, Report
from backend.contracts.signal import Signal
from backend.intelligence.engine import build_intelligence


def build_report(
    signals: List[Signal],
    models_run: List[str],
    annotated_image: Optional[str] = None,
) -> Report:
    intel = build_intelligence(signals)  # {graph, risks, attackPath, fixes}
    return Report(
        annotatedImage=annotated_image,
        signals=signals,
        graph=intel["graph"],
        risks=intel["risks"],
        attackPath=intel["attackPath"],
        fixes=intel["fixes"],
        meta=Meta(
            processedLocally=True,
            stored=False,  # uploads are processed in-memory, never written to disk
            modelsRun=models_run,
        ),
    )
