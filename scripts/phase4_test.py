"""Phase 4 acceptance test — intelligence engines (graph/risk/attack/fix).

Pure, deterministic, no GPU/ML/LLM. Runs build_intelligence over
fixtures/signals_sample.json (15 signals, every type) and pins the outputs.

    python -m scripts.phase4_test
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.contracts.signal import Signal
from backend.intelligence.engine import build_intelligence
from backend.intelligence.graph import build_graph
from backend.intelligence.risk import score_risks

ROOT = Path(__file__).resolve().parent.parent


def _signals():
    raw = json.loads((ROOT / "fixtures" / "signals_sample.json").read_text(encoding="utf-8"))
    return [Signal.model_validate(s) for s in raw]


def test_risks_matrix() -> None:
    r = score_risks(_signals())
    # gps+face(30) ; gps+face+home(dox40,stalk20) ; employer+email(phish25) ;
    # location+username(stalk20) ; email|phone(dox10,phish20) ; face+username(dox15)
    assert (r.doxxing, r.stalking, r.phishing) == (65, 70, 45), (r.doxxing, r.stalking, r.phishing)
    print(f"risk matrix       -> doxxing={r.doxxing} stalking={r.stalking} phishing={r.phishing} (matches fixture). [OK]")


def test_graph() -> None:
    g = build_graph(_signals())
    ids = {n.id for n in g.nodes}
    assert "user" in ids and {n.type for n in g.nodes if n.id == "user"} == {"user"}
    for nid in ("face_visible", "employer_known", "username_known", "gps_known", "home_indicator"):
        assert nid in ids, nid
    # fusion nodes (the named-innovation highlight)
    assert "home_locatable" in ids and "identity_linkable" in ids
    # every edge points at a real node; user is the hub
    node_ids = {n.id for n in g.nodes}
    assert all(e.source in node_ids and e.target in node_ids for e in g.edges)
    assert any(e.source == "user" and e.label == "is exposed via" for e in g.edges)
    print(f"exposure graph    -> {len(g.nodes)} nodes, {len(g.edges)} edges, 2 fusion nodes. [OK]")


def test_attack() -> None:
    steps = build_intelligence(_signals())["attackPath"]
    assert len(steps) == 5, steps                       # face+employer+username template
    assert "ACME Corp" in steps[0] and "johndoe" in steps[3]
    assert "phishing" in steps[-1].lower() and "possible" in steps[-1].lower()  # hypothetical endpoint
    print(f"attack path       -> {len(steps)} steps, parametrized + hypothetical endpoint. [OK]")


def test_fixes() -> None:
    fixes = build_intelligence(_signals())["fixes"]
    issues = [f.issue for f in fixes]
    assert "EXIF GPS" in issues and len(fixes) == 6
    assert sum(1 for f in fixes if f.oneClick) == 1                  # only the EXIF strip is one-click
    assert len(issues) == len(set(issues))                          # de-duped
    print(f"fix engine        -> {len(fixes)} fixes, 1 one-click (EXIF GPS), de-duped. [OK]")


def test_empty_and_determinism() -> None:
    out = build_intelligence([])
    assert (out["risks"].doxxing, out["risks"].stalking, out["risks"].phishing) == (0, 0, 0)
    assert out["attackPath"] == [] and out["fixes"] == []
    assert len(out["graph"].nodes) == 1 and out["graph"].nodes[0].id == "user"  # honest when clean
    # determinism: same signals -> identical graph dump
    a = build_graph(_signals()).model_dump()
    b = build_graph(_signals()).model_dump()
    assert a == b
    print("empty + determinism -> clean input -> just the user node; output is stable. [OK]")


def main() -> int:
    test_risks_matrix()
    test_graph()
    test_attack()
    test_fixes()
    test_empty_and_determinism()
    print("\nAll Phase 4 intelligence assertions passed. [PASS]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
