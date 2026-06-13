"""Attack-Path Generator (PLAN §4.9) — PHASE 4 LANE.

Match the present signal set against templates -> an ordered, human-readable
narrative of how a stranger could chain the exposed data. Templates guarantee a
coherent story every time, no model required.

CONTRACT (engine.py already calls it):  build_attack_path(signals) -> List[str]

ETHICS (PLAN §4.9): the recon steps describe what an attacker *would* do; the
harmful endpoint stays HYPOTHETICAL ("possible") — the tool never performs any of it.
"""
from __future__ import annotations

from typing import List

from backend.contracts.signal import Signal


def _first(signals: List[Signal], t: str, default: str) -> str:
    for s in signals:
        if s.type == t and s.value:
            return s.value
    return default


def build_attack_path(signals: List[Signal]) -> List[str]:
    t = {s.type for s in signals}
    employer = _first(signals, "employer", "your employer")
    username = _first(signals, "username", "your handle").split(" (")[0]
    contact = "exposed email" if "email" in t else ("exposed phone" if "phone" in t else "exposed contact")

    # Highest-signal template first (PLAN §4.9 trigger table).
    if {"face", "employer", "username"} <= t:
        return [
            f"Employer identified from the exposed text ({employer}).",
            "Employee profiles searched on the company site.",
            "Face cross-referenced against public profiles.",
            f"Other linked accounts discovered via the username '{username}'.",
            f"Targeted phishing to the {contact} becomes possible.",
        ]
    if {"gps", "home_indicator", "face"} <= t:
        return [
            "Home location pinned from the photo's GPS metadata.",
            "Domestic objects in frame confirm it as a residence.",
            "The visible face makes the occupant identifiable on sight.",
        ]
    if {"location", "timestamp"} <= t:
        return [
            "Daily routine inferred from the caption's location and the timestamp.",
            "Predictable presence at that place/time becomes targetable.",
        ]
    return []
