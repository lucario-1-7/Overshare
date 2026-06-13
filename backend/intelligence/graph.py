"""Exposure Graph builder (PLAN §4.7) — PHASE 4 LANE.

THE PROJECT'S NAMED INNOVATION. Turns the set of present signal types into a
User-centred graph (react-flow on the frontend), with FUSION nodes that highlight
that combined signals are worse than the sum.

CONTRACT (engine.py already calls it):  build_graph(signals) -> Graph

Node ids mirror fixtures/report_sample.json so the Phase 5 UI renders real output
identically. Deterministic: same signal set -> same graph, every time.
"""
from __future__ import annotations

from typing import Callable, Dict, List

from backend.contracts.report import Graph, GraphEdge, GraphNode
from backend.contracts.signal import Signal


def _short_loc(v: str) -> str:
    return v.split(",")[0].strip() if v else v


def _handle(v: str) -> str:
    return v.split(" (")[0].strip() if v else v  # "johndoe (github)" -> "johndoe"


# Only "exposure-worthy" types become nodes. Raw/auxiliary types (device, timestamp,
# screen_text, person, document) feed fusions / attack paths but aren't headline nodes.
# type -> (stable node id, label builder from a representative value)
_NODE_SPEC: Dict[str, "tuple[str, Callable[[str], str]]"] = {
    "face":           ("face_visible",    lambda v: "Face Visible"),
    "person_name":    ("name_known",      lambda v: f"Name: {v}"),
    "employer":       ("employer_known",  lambda v: f"Employer: {v}"),
    "email":          ("email_exposed",   lambda v: "Email Exposed"),
    "phone":          ("phone_exposed",   lambda v: "Phone Exposed"),
    "location":       ("location_known",  lambda v: f"Location: {_short_loc(v)}"),
    "address":        ("address_known",   lambda v: f"Address: {v}"),
    "username":       ("username_known",  lambda v: f"Username: {_handle(v)}"),
    "gps":            ("gps_known",       lambda v: "GPS Location"),
    "home_indicator": ("home_indicator",  lambda v: f"Home Indicator: {v}"),
}
# Stable render order (deterministic node ordering).
_ORDER = [
    "face", "person_name", "employer", "email", "phone",
    "location", "address", "username", "gps", "home_indicator",
]


def _first_value(signals: List[Signal], t: str) -> str:
    for s in signals:
        if s.type == t and s.value:
            return s.value
    return ""


def build_graph(signals: List[Signal]) -> Graph:
    present = {s.type for s in signals}
    nodes: List[GraphNode] = [GraphNode(id="user", label="You", type="user")]
    edges: List[GraphEdge] = []
    ids: Dict[str, str] = {}

    for t in _ORDER:
        if t in present and t in _NODE_SPEC:
            nid, label_fn = _NODE_SPEC[t]
            try:
                label = label_fn(_first_value(signals, t))
            except Exception:
                label = t
            nodes.append(GraphNode(id=nid, label=label, type=t))
            edges.append(GraphEdge(source="user", target=nid, label="is exposed via"))
            ids[t] = nid

    # Fusion: GPS + a home indicator => the home is locatable (worse than either alone).
    if "gps" in ids and "home_indicator" in ids:
        nodes.append(GraphNode(id="home_locatable", label="Home Locatable", type="fusion"))
        edges.append(GraphEdge(source=ids["gps"], target="home_locatable", label="GPS + home indicator"))
        edges.append(GraphEdge(source=ids["home_indicator"], target="home_locatable", label="GPS + home indicator"))
        edges.append(GraphEdge(source="user", target="home_locatable", label="fused risk"))

    # Fusion: a visible face + a reused username => face tied to your other accounts.
    if "face" in ids and "username" in ids:
        nodes.append(GraphNode(id="identity_linkable", label="Identity Linkable", type="fusion"))
        edges.append(GraphEdge(source=ids["face"], target="identity_linkable", label="face <-> accounts"))
        edges.append(GraphEdge(source=ids["username"], target="identity_linkable", label="face <-> accounts"))
        edges.append(GraphEdge(source="user", target="identity_linkable", label="fused risk"))

    return Graph(nodes=nodes, edges=edges)
