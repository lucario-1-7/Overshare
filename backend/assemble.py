"""Report assembly (PLAN §3 step 11, §4.12).

Takes the populated signals[] and builds a schema-valid Report. In Phase 1 the
graph / risks / attackPath / fixes default to valid-but-empty; Phase 2+ wires in
the Exposure Graph, Risk Engine, Attack-Path Generator and Fix Engine here.
"""
from __future__ import annotations

from typing import List, Optional

from backend.contracts.report import Meta, Report
from backend.contracts.signal import Signal


def build_report(
    signals: List[Signal],
    models_run: List[str],
    annotated_image: Optional[str] = None,
) -> Report:
    return Report(
        annotatedImage=annotated_image,
        signals=signals,
        meta=Meta(
            processedLocally=True,
            stored=False,  # uploads are processed in-memory, never written to disk
            modelsRun=models_run,
        ),
    )
