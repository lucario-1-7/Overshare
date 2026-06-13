"""Attack-Path Generator (PLAN §4.9) — PHASE 4 LANE.  [STUB — fill this in]

Match the present signal set against templates -> an ordered, human-readable
narrative of how a stranger could chain the exposed data. Templates guarantee a
coherent story every time, no model required.

CONTRACT (do not change the signature; engine.py already calls it):
    build_attack_path(signals) -> List[str]    # ordered steps

Trigger table (PLAN §4.9):
    face + employer + username ->
        1 Employer identified  2 employee profiles searched
        3 face cross-referenced  4 other accounts found  5 targeted phishing possible
    gps + home_indicator + face ->
        1 Home location pinned from GPS  2 confirmed as residence
        3 occupant identifiable on sight
    location(caption) + timestamp ->
        1 routine inferred  2 predictable presence at a place/time

Pick the highest-signal template that matches; return [] if nothing matches.
ETHICS: steps are HYPOTHETICAL ("could", "possible") — the tool never performs them.
"""
from __future__ import annotations

from typing import List

from backend.contracts.signal import Signal


def build_attack_path(signals: List[Signal]) -> List[str]:
    """PHASE 4: select a template by the present signal set; return ordered steps.
    Stub returns [] (current behavior)."""
    # TODO(phase4): match {s.type for s in signals} to a template; return its steps.
    return []
