"""Digital Footprint engine — deterministic scoring + metrics over footprint signals.

Pure functions (no network, no randomness): same signals -> same report. Turns the
collected footprint signals into category scores, a composite Footprint Score, an
attacker-effort estimate, an inference-amplification metric, and a time-to-exploit
timeline. This is the "product" layer that makes the external signals legible.
"""
from __future__ import annotations

from typing import List, Optional

from .models import Category, FootprintReport, FootprintSignal, TimelineStep


def _clamp(x: float) -> int:
    return 0 if x < 0 else 100 if x > 100 else int(round(x))


def build_footprint(
    email: Optional[str],
    username: Optional[str],
    signals: List[FootprintSignal],
) -> FootprintReport:
    platforms = [s for s in signals if s.type == "platform_presence"]
    n_platforms = len(platforms)
    breach = next((s for s in signals if s.type == "breach_exposure"), None)
    breach_count = int((breach.detail or {}).get("count", 0)) if breach else 0
    is_corporate = any(s.type == "email_domain" and s.value == "corporate" for s in signals)
    is_personal = any(s.type == "email_domain" and s.value == "personal" for s in signals)
    has_gravatar = any(s.type == "gravatar_profile" for s in signals)
    has_email = bool(email)

    # --- category scores (0–100, deterministic) ---
    personal_identity = _clamp((40 if has_gravatar else 0) + n_platforms * 15)
    professional_identity = _clamp(
        (80 if is_corporate else 30 if is_personal else 0)
        + (20 if any((p.detail or {}).get("site") in {"github", "gitlab"} for p in platforms) else 0)
    )
    contactability = _clamp((50 if has_email else 0) + min(50, breach_count * 15))
    cross_platform = _clamp(n_platforms * 20)

    categories = [
        Category(name="Personal identity", score=personal_identity),
        Category(name="Professional identity", score=professional_identity),
        Category(name="Contactability", score=contactability),
        Category(name="Cross-platform presence", score=cross_platform),
    ]
    footprint_score = _clamp(sum(c.score for c in categories) / len(categories))

    # --- attacker effort (low effort for them == high exposure for you) ---
    if footprint_score >= 70:
        effort = {"level": "LOW", "eta": "< 5 minutes"}
    elif footprint_score >= 40:
        effort = {"level": "MEDIUM", "eta": "~30 minutes"}
    else:
        effort = {"level": "HIGH", "eta": "hours+"}

    # --- inference amplification (raw inputs -> derived inferences) ---
    raw_inputs = (1 if email else 0) + (1 if username else 0)
    derived = len(signals)
    amplification = {
        "rawInputs": raw_inputs,
        "derivedInferences": derived,
        "factor": round(derived / raw_inputs, 2) if raw_inputs else 0.0,
    }

    # --- time-to-exploit timeline ---
    timeline: List[TimelineStep] = []
    if email or username:
        timeline.append(TimelineStep(t="T+0s", label="Identifier captured (email / username)"))
    if n_platforms:
        sites = ", ".join(sorted({(p.detail or {}).get("site", "?") for p in platforms}))
        timeline.append(TimelineStep(t="T+30s", label=f"{n_platforms} public account(s) found ({sites})"))
    if is_corporate:
        timeline.append(TimelineStep(t="T+1m", label="Employer inferred from the email domain"))
    if breach_count:
        timeline.append(TimelineStep(t="T+2m", label=f"Credentials exposed in {breach_count} known breach(es)"))
    if footprint_score >= 40:
        timeline.append(TimelineStep(t="T+5m", label="Signals cross-referenced into a single identity"))
        timeline.append(TimelineStep(t="T+15m", label="Targeted phishing / account takeover becomes feasible"))

    sent = [k for k, v in (("email", email), ("username", username)) if v]
    return FootprintReport(
        inputs={"email": email, "username": username},
        signals=signals,
        categories=categories,
        footprintScore=footprint_score,
        attackerEffort=effort,
        amplification=amplification,
        timeline=timeline,
        meta={
            "sourcesQueried": ["xposedornot", "gravatar", "presence"],
            "sentToExternal": sent,  # only the identifier(s) you entered left the machine — never an image
            "note": "Image analysis stays local; footprint lookups send only the identifier you provide.",
        },
    )
