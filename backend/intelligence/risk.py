"""Risk Engine (PLAN §4.8) — PHASE 4 LANE.  [STUB — fill this in]

Deterministic rules over the SET of present signal types -> three 0–100 scores.
Deterministic = demo-safe (same input -> same score) and explainable.

CONTRACT (do not change the signature; engine.py already calls it):
    score_risks(signals) -> Risks        # from backend.contracts.report  {doxxing, stalking, phishing}

Connection matrix (PLAN §4.8) — add the points, then clamp each to [0, 100]:
    gps + face                          -> stalking +30
    gps + face + home_indicator         -> doxxing +40, stalking +20
    employer + (email | person_name)    -> phishing +25
    location + username                 -> stalking +20
    email | phone exposed               -> doxxing +10, phishing +20
    face + username                     -> doxxing +15

Tip: compute over a set of types, e.g. `t = {s.type for s in signals}`.
"""
from __future__ import annotations

from typing import List

from backend.contracts.report import Risks
from backend.contracts.signal import Signal


def score_risks(signals: List[Signal]) -> Risks:
    """PHASE 4: apply the connection matrix and return clamped 0–100 scores.
    Stub returns all-zero (current behavior)."""
    # TODO(phase4): t = {s.type for s in signals}; accumulate per the matrix; clamp 0..100.
    return Risks()
