"""Footprint pipeline (PLAN §4.4, §10) — PHASE 3 LANE.

Username/email existence checks via `requests` (no ML model). Probes a handful of
public sites and emits a `username` Signal per site where the handle exists.

CONTRACT (do not change the signature; router.py already calls it):
    extract_footprint_signals(username) -> List[Signal]

Reliability (PLAN §10): live checks get rate-limited/blocked at demo time, so:
  - every HTTP call is bounded by a short timeout and fully guarded (never raises),
  - a CANNED fallback (env `OVERSHARE_CANNED=1`, or a known demo handle) returns
    deterministic hits so the demo never hangs or comes back empty.
"""
from __future__ import annotations

import os
from typing import List, Optional, Tuple

from backend.contracts.signal import Evidence, Signal

_TIMEOUT = 4.0  # seconds per site — short so a slow/blocking site can't stall the request
_UA = {"User-Agent": "Mozilla/5.0 (OvershareBot; privacy self-audit)"}

# Public sites whose profile URL 404s cleanly for a missing handle.
# (site, url_template, confidence_if_found)
_SITES: List[Tuple[str, str, float]] = [
    ("github", "https://github.com/{u}", 0.95),
    ("reddit", "https://www.reddit.com/user/{u}/about.json", 0.9),
    ("gitlab", "https://gitlab.com/{u}", 0.85),
    ("devto", "https://dev.to/{u}", 0.85),
]

# Demo fallback so a rate-limited live run still shows the feature (PLAN §10).
_CANNED = {
    "johndoe": [("github", "https://github.com/johndoe", 0.95),
                ("reddit", "https://www.reddit.com/user/johndoe", 0.9)],
}


def _normalize(username: str) -> str:
    h = username.strip().lstrip("@")
    if "@" in h:  # an email was passed — probe sites with the local part
        h = h.split("@", 1)[0]
    return h


def _valid_handle(h: str) -> bool:
    return bool(h) and 1 <= len(h) <= 39 and all(c.isalnum() or c in "-_." for c in h)


def _canned(handle: str) -> List[Signal]:
    out: List[Signal] = []
    for site, url, conf in _CANNED.get(handle.lower(), []):
        out.append(
            Signal(
                type="username",
                value=f"{handle} ({site})",
                source="footprint",
                confidence=conf,
                evidence=Evidence(text=url, raw={"site": site, "canned": True}),
            )
        )
    return out


def extract_footprint_signals(username: str) -> List[Signal]:
    """Probe public sites for `username`; emit a `username` Signal per hit.
    Returns [] if username is empty/invalid or on any error."""
    if not username or not username.strip():
        return []
    handle = _normalize(username)
    if not _valid_handle(handle):
        return []

    # Canned mode (demo safety): explicit env flag, or a known demo handle.
    if os.environ.get("OVERSHARE_CANNED") == "1" or handle.lower() in _CANNED:
        canned = _canned(handle)
        if canned:
            return canned

    try:
        import requests
    except Exception:  # requests not installed -> degrade silently
        return _canned(handle)

    signals: List[Signal] = []
    for site, template, conf in _SITES:
        url = template.format(u=handle)
        try:
            resp = requests.get(url, headers=_UA, timeout=_TIMEOUT, allow_redirects=True)
            if resp.status_code == 200:
                # reddit's about.json returns 200 with an empty/error body for some states
                profile = url.replace("/about.json", "")
                signals.append(
                    Signal(
                        type="username",
                        value=f"{handle} ({site})",
                        source="footprint",
                        confidence=conf,
                        evidence=Evidence(text=profile, raw={"site": site, "status": 200}),
                    )
                )
        except Exception:
            continue  # timeout / blocked / network error -> just skip that site
    return signals
