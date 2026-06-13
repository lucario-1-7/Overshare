"""Fix Engine (PLAN §4.10) — PHASE 4 LANE.

Map each PRESENT risky signal type to a concrete remediation. The one-click
EXIF-GPS strip is the satisfying demo closer.

CONTRACT (engine.py already calls it):  suggest_fixes(signals) -> List[Fix]

Only emits a fix for a type that is actually present; de-duped by issue. Wording +
order mirror fixtures/report_sample.json so the Phase 5 UI matches real output.
"""
from __future__ import annotations

from typing import List

from backend.contracts.report import Fix
from backend.contracts.signal import Signal


def suggest_fixes(signals: List[Signal]) -> List[Fix]:
    t = {s.type for s in signals}
    fixes: List[Fix] = []
    seen: set = set()

    def add(issue: str, action: str, one_click: bool = False) -> None:
        if issue not in seen:
            seen.add(issue)
            fixes.append(Fix(issue=issue, action=action, oneClick=one_click))

    if "gps" in t:
        add("EXIF GPS", "Strip EXIF GPS & re-download a clean image", True)  # the one-click closer
    if "face" in t:
        add("Face visible", "Blur faces / avoid identifiable shots")
    if "employer" in t:
        add("Employer badge", "Crop the lanyard/badge before posting")
    if "location" in t:
        add("Location in caption", "Remove the place name from the caption")
    if "email" in t or "phone" in t:
        add("Contact info", "Redact the exposed email/phone")
    if "username" in t:
        add("Username footprint", "Lock down / unlink exposed profiles")

    return fixes
