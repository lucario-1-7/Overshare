"""Fix Engine (PLAN §4.10) — PHASE 4 LANE.  [STUB — fill this in]

Map each risky signal to a concrete remediation. The one-click EXIF-GPS strip is the
satisfying demo closer.

CONTRACT (do not change the signature; engine.py already calls it):
    suggest_fixes(signals) -> List[Fix]        # from backend.contracts.report

Fix(issue, action, oneClick). Mapping (PLAN §4.10):
    gps          -> "Strip EXIF GPS & re-download clean image"   oneClick=True
    face         -> "Blur faces / avoid identifiable shots"      oneClick=False
    employer     -> "Crop the lanyard/badge before posting"      oneClick=False
    location     -> "Remove the place name from the caption"     oneClick=False
    email|phone  -> "Redact contact info"                        oneClick=False
    username     -> "Lock down / unlink exposed profiles"        oneClick=False

Only emit a fix for a signal type that is actually present. De-dup by issue.
"""
from __future__ import annotations

from typing import List

from backend.contracts.report import Fix
from backend.contracts.signal import Signal


def suggest_fixes(signals: List[Signal]) -> List[Fix]:
    """PHASE 4: map present risky signal types to Fix entries (de-duped).
    Stub returns [] (current behavior)."""
    # TODO(phase4): for each present risky type, append the mapped Fix; de-dup by issue.
    return []
