"""Risk Engine (PLAN §4.8) — PHASE 4 LANE.

Deterministic rules over the SET of present signal types -> three 0–100 scores.
Deterministic = demo-safe (same input -> same score) and explainable
("82 because gps+face+home"). NOT AI — pure rules.

CONTRACT (engine.py already calls it):  score_risks(signals) -> Risks {doxxing, stalking, phishing}
"""
from __future__ import annotations

from typing import List

from backend.contracts.report import Risks
from backend.contracts.signal import Signal


def _clamp(x: int) -> int:
    return 0 if x < 0 else 100 if x > 100 else int(x)


def score_risks(signals: List[Signal]) -> Risks:
    t = {s.type for s in signals}
    doxxing = stalking = phishing = 0

    # PLAN §4.8 connection matrix — additive, then clamped.
    if "gps" in t and "face" in t:
        stalking += 30
    if "gps" in t and "face" in t and "home_indicator" in t:
        doxxing += 40
        stalking += 20
    if "employer" in t and ("email" in t or "person_name" in t):
        phishing += 25
    if "location" in t and "username" in t:
        stalking += 20
    if "email" in t or "phone" in t:
        doxxing += 10
        phishing += 20
    if "face" in t and "username" in t:
        doxxing += 15

    return Risks(doxxing=_clamp(doxxing), stalking=_clamp(stalking), phishing=_clamp(phishing))
