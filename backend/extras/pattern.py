"""Multi-Post Pattern Engine — EXTRAS (additive, deterministic, no LLM/GPU/API).

A digital footprint is built across MANY posts, not one. This aggregates the core
`signals[]` from N uploads into a footprint profile: frequency, recurring entities,
exposure consistency, exposure trend, and transparent insights ("Microsoft in 7/10
posts -> recurring professional exposure").

Reads the core read-only (`Signal`, `score_risks`) — it never modifies it.
"""
from __future__ import annotations

import math
from collections import Counter
from typing import List

from backend.contracts.signal import Signal          # read-only import
from backend.intelligence.risk import score_risks     # read-only import

from .models import ProfileInsight, ProfileReport, RecurringEntity

# Types that represent a real identity/exposure leak (used for "consistency").
_SENSITIVE = {
    "gps", "face", "person_name", "employer", "organization", "email", "phone",
    "home_indicator", "address", "location", "username",
}


def _exposure(signals: List[Signal]) -> int:
    """Single 0–100 exposure number for one post (max of the core risk scores)."""
    try:
        r = score_risks(signals)
        return max(int(r.doxxing), int(r.stalking), int(r.phishing))
    except Exception:
        return 0


def _trend(scores: List[int]) -> str:
    if len(scores) < 2:
        return "n/a"
    mid = len(scores) // 2
    first = sum(scores[:mid]) / max(mid, 1)
    second = sum(scores[mid:]) / max(len(scores) - mid, 1)
    if second >= first + 10:
        return "increasing"
    if second <= first - 10:
        return "decreasing"
    return "stable"


def build_profile(posts: List[List[Signal]]) -> ProfileReport:
    """Aggregate per-post signal lists into a footprint profile. Pure + deterministic."""
    total = len(posts)
    if total == 0:
        return ProfileReport(totalPosts=0)

    # posts-containing count per type (presence-per-post, not raw occurrences)
    type_posts: Counter = Counter()
    # posts-containing count per (type, value) -> recurring entities
    value_posts: Counter = Counter()
    per_post_scores: List[int] = []
    posts_with_sensitive = 0

    for sigs in posts:
        per_post_scores.append(_exposure(sigs))
        types_here = {s.type for s in sigs}
        for t in types_here:
            type_posts[t] += 1
        for s in sigs:
            value_posts[(s.type, s.value)] += 1
        if types_here & _SENSITIVE:
            posts_with_sensitive += 1

    signal_frequency = dict(sorted(type_posts.items(), key=lambda kv: (-kv[1], kv[0])))

    # Recurring entities: same (type,value) seen in >=2 posts, identity-bearing types.
    recurring: List[RecurringEntity] = []
    for (t, v), n in value_posts.most_common():
        if n >= 2 and t in {"employer", "organization", "location", "person_name", "username"}:
            recurring.append(RecurringEntity(type=t, value=v, posts=n, totalPosts=total))

    exposure_consistency = round(100 * posts_with_sensitive / total)
    trend = _trend(per_post_scores)
    footprint_score = round(
        0.6 * (sum(per_post_scores) / total) + 0.4 * exposure_consistency
    )
    footprint_score = max(0, min(100, footprint_score))

    # --- transparent, rule-based insights ---
    insights: List[ProfileInsight] = []
    half = max(2, math.ceil(total * 0.5))

    for ent in recurring:
        if ent.type in {"employer", "organization"} and ent.posts >= max(2, math.ceil(total * 0.4)):
            conf = "High" if ent.posts >= half else "Medium"
            insights.append(ProfileInsight(
                kind="professional_identity",
                label=f"Recurring employer exposure: {ent.value} (Professional Identity Confidence: {conf})",
                evidence=f"{ent.value} appears in {ent.posts}/{total} posts",
            ))
    if type_posts.get("face", 0) >= half:
        insights.append(ProfileInsight(
            kind="persistent_identity",
            label="Persistent identity exposure",
            evidence=f"A face is visible in {type_posts['face']}/{total} posts",
        ))
    loc_posts = type_posts.get("location", 0) + type_posts.get("gps", 0)
    if loc_posts >= 2:
        insights.append(ProfileInsight(
            kind="location_disclosure",
            label="Repeated location disclosure",
            evidence=f"Location/GPS present in {loc_posts} post-occurrences",
        ))
    for ent in recurring:
        if ent.type == "location" and ent.posts >= 2:
            insights.append(ProfileInsight(
                kind="routine_pattern",
                label=f"Routine pattern detected: {ent.value}",
                evidence=f"{ent.value} seen in {ent.posts}/{total} posts",
            ))
    if exposure_consistency >= 60:
        insights.append(ProfileInsight(
            kind="exposure_consistency",
            label=f"High exposure consistency ({exposure_consistency}%)",
            evidence=f"{posts_with_sensitive}/{total} posts leak identity information",
        ))
    if trend == "increasing":
        insights.append(ProfileInsight(
            kind="exposure_trend",
            label="Exposure trend: increasing",
            evidence=f"per-post exposure rose across the {total} posts",
        ))

    return ProfileReport(
        totalPosts=total,
        signalFrequency=signal_frequency,
        recurringEntities=recurring,
        exposureConsistency=exposure_consistency,
        exposureTrend=trend,
        perPostScores=per_post_scores,
        footprintScore=footprint_score,
        insights=insights,
    )
