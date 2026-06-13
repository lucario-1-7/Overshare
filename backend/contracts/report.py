"""The Report contract — the frontend's only interface to the backend (PLAN §4.12).

The UI is dumb: it renders this object into fixed sections and nothing else.
In Phase 1, graph / risks / attackPath / fixes are valid-but-empty placeholders;
later phases fill them in without changing the shape.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .signal import Signal


class GraphNode(BaseModel):
    id: str
    label: str
    type: Optional[str] = None          # e.g. "user", "face", "employer"
    data: Optional[Dict[str, Any]] = None


class GraphEdge(BaseModel):
    source: str
    target: str
    label: Optional[str] = None         # e.g. "is exposed via"


class Graph(BaseModel):
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)


class Risks(BaseModel):
    doxxing: int = 0                    # 0–100, clamped by the Risk Engine
    stalking: int = 0
    phishing: int = 0


class Fix(BaseModel):
    issue: str
    action: str
    oneClick: bool = False


class Meta(BaseModel):
    processedLocally: bool = True
    stored: bool = False                # "nothing left this machine" — the differentiator
    modelsRun: List[str] = Field(default_factory=list)


class Report(BaseModel):
    annotatedImage: Optional[str] = None  # "data:image/png;base64,..."
    signals: List[Signal] = Field(default_factory=list)
    graph: Graph = Field(default_factory=Graph)
    risks: Risks = Field(default_factory=Risks)
    attackPath: List[str] = Field(default_factory=list)
    fixes: List[Fix] = Field(default_factory=list)
    explanation: Optional[str] = None     # optional LLM paragraph
    meta: Meta = Field(default_factory=Meta)
