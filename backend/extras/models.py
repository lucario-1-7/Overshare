"""Extras result models — independent of the frozen core contracts on purpose.

Keeping these separate is what lets the extras package add new signal kinds
(breach_exposure, platform_presence, email_domain, gravatar_profile) WITHOUT
editing backend/contracts/ — so the core stays byte-identical.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class FootprintSignal(BaseModel):
    type: str                                   # breach_exposure | platform_presence | email_domain | gravatar_profile | organization
    value: str
    source: str                                 # xposedornot | presence | domain | gravatar
    detail: Optional[Dict[str, Any]] = None


class Category(BaseModel):
    name: str
    score: int                                  # 0–100


class TimelineStep(BaseModel):
    t: str                                      # "T+0s", "T+30s", "T+2m", ...
    label: str


class FootprintReport(BaseModel):
    inputs: Dict[str, Optional[str]] = Field(default_factory=dict)   # {email, username}
    signals: List[FootprintSignal] = Field(default_factory=list)
    categories: List[Category] = Field(default_factory=list)
    footprintScore: int = 0                     # 0–100 composite
    attackerEffort: Dict[str, Any] = Field(default_factory=dict)     # {level, eta}
    amplification: Dict[str, Any] = Field(default_factory=dict)      # {rawInputs, derivedInferences, factor}
    timeline: List[TimelineStep] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)               # {sourcesQueried, sentToExternal, note}


# --- Multi-post profile analysis (Pattern Engine) ---
class RecurringEntity(BaseModel):
    type: str
    value: str
    posts: int                                  # how many posts it appeared in
    totalPosts: int


class ProfileInsight(BaseModel):
    kind: str
    label: str
    evidence: str                               # the transparent "how we know" line


class ProfileReport(BaseModel):
    totalPosts: int = 0
    signalFrequency: Dict[str, int] = Field(default_factory=dict)    # type -> posts-containing
    recurringEntities: List[RecurringEntity] = Field(default_factory=list)
    exposureConsistency: int = 0                # % of posts leaking identity info
    exposureTrend: str = "n/a"                  # increasing | decreasing | stable | n/a
    perPostScores: List[int] = Field(default_factory=list)
    footprintScore: int = 0
    insights: List[ProfileInsight] = Field(default_factory=list)
