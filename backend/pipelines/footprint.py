"""Footprint pipeline (PLAN §4.4, §10) — PHASE 3 LANE.  [STUB — fill this in]

Username/email existence checks via `requests` (no ML model). For a handle, probe a
handful of public sites and emit a `username` Signal per site where it exists.

CONTRACT (do not change the signature; router.py already calls it):
    extract_footprint_signals(username) -> List[Signal]

Each emitted Signal MUST be:
    type     = "username"
    source   = "footprint"
    value    = e.g. "johndoe (github)"   # handle + where it was found
    confidence = your confidence the account exists (in [0, 1])
    evidence = Evidence(text=<profile URL>)

Reliability (PLAN §10): live checks can be rate-limited at demo time. Keep a small
CANNED fallback (a hardcoded handle->sites map) behind a flag so the demo never hangs.
Rules: never raise (return []); bound every HTTP call with a short timeout.
"""
from __future__ import annotations

from typing import List

from backend.contracts.signal import Signal  # noqa: F401  (used once implemented)


def extract_footprint_signals(username: str) -> List[Signal]:
    """PHASE 3: probe public sites for `username`; emit a `username` Signal per hit.
    Return [] if username is empty or on any error."""
    if not username or not username.strip():
        return []
    # TODO(phase3): requests.get per site with timeout; map existing profiles -> Signals.
    return []
