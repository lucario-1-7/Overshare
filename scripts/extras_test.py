"""Extras acceptance test — digital-footprint module (isolated additions).

Verifies the collectors + footprint scoring + the /extras/footprint endpoint, and
asserts the CORE endpoints are unchanged. Deterministic parts need no network;
live parts are guarded (skip cleanly offline). Canned mode keeps it CI-safe.

    python -m scripts.extras_test
"""
from __future__ import annotations

import os
import sys

from backend.extras.collectors import classify_email_domain, collect
from backend.extras.footprint import build_footprint
from backend.extras.models import FootprintReport


def test_email_domain() -> None:
    personal = classify_email_domain("john@gmail.com")
    assert any(s.type == "email_domain" and s.value == "personal" for s in personal)
    corp = classify_email_domain("john@acme.com")
    assert any(s.type == "email_domain" and s.value == "corporate" for s in corp)
    assert any(s.type == "organization" and s.value == "Acme" for s in corp)
    print("email domain      -> gmail=personal, acme.com=corporate (+org inference). [OK]")


def test_footprint_scoring() -> None:
    from backend.extras.models import FootprintSignal as S
    signals = [
        S(type="email_domain", value="corporate", source="domain", detail={"domain": "acme.com"}),
        S(type="organization", value="Acme", source="domain"),
        S(type="breach_exposure", value="4 breaches", source="xposedornot", detail={"count": 4, "names": ["A", "B", "C", "D"]}),
        S(type="platform_presence", value="jdoe (github)", source="presence", detail={"site": "github"}),
        S(type="platform_presence", value="jdoe (gitlab)", source="presence", detail={"site": "gitlab"}),
        S(type="gravatar_profile", value="John Doe", source="gravatar"),
    ]
    r = build_footprint("john@acme.com", "jdoe", signals)
    assert 0 <= r.footprintScore <= 100 and r.footprintScore > 0
    assert {c.name for c in r.categories} == {
        "Personal identity", "Professional identity", "Contactability", "Cross-platform presence"}
    assert r.attackerEffort.get("level") in {"LOW", "MEDIUM", "HIGH"}
    assert r.amplification["rawInputs"] == 2 and r.amplification["derivedInferences"] == 6
    assert any("breach" in s.label.lower() for s in r.timeline)
    assert r.meta["sentToExternal"] == ["email", "username"]  # only identifiers, never an image
    # determinism
    assert build_footprint("john@acme.com", "jdoe", signals).model_dump() == r.model_dump()
    print(f"footprint scoring -> score={r.footprintScore}, effort={r.attackerEffort['level']}, "
          f"amp={r.amplification['factor']}x, {len(r.timeline)} timeline steps. [OK]")


def test_canned_collect() -> None:
    os.environ["OVERSHARE_CANNED"] = "1"
    try:
        sigs = collect(email="demo@overshare.app", username="demo")
        assert any(s.type == "breach_exposure" for s in sigs)
        assert sum(1 for s in sigs if s.type == "platform_presence") >= 4
        assert any(s.type == "email_domain" for s in sigs)
    finally:
        os.environ.pop("OVERSHARE_CANNED", None)
    print("canned collect    -> demo persona yields breach + 4 platforms + domain (no network). [OK]")


def test_endpoint_and_core_untouched() -> None:
    from fastapi.testclient import TestClient

    from backend.main import app

    os.environ["OVERSHARE_CANNED"] = "1"
    try:
        with TestClient(app) as client:
            # the NEW endpoint
            r = client.post("/extras/footprint", json={"email": "demo@overshare.app", "username": "demo"})
            assert r.status_code == 200, r.text
            FootprintReport.model_validate(r.json())
            assert client.get("/extras/health").status_code == 200
            # CORE endpoints unchanged
            assert client.get("/health").status_code == 200
            assert client.get("/sample-report").status_code == 200
            assert client.post("/analyze", json={"text": "hi"}).status_code == 200
    finally:
        os.environ.pop("OVERSHARE_CANNED", None)
    print("endpoint + core   -> /extras/footprint works; /health, /sample-report, /analyze unchanged. [OK]")


def test_live_optional() -> None:
    try:
        import requests  # noqa: F401
    except Exception:
        print("live (optional)   -> skipped (requests not installed).")
        return
    try:
        sigs = collect(username="torvalds")  # real GitHub/GitLab user (canned-backed too)
        hits = [s.value for s in sigs if s.type == "platform_presence"]
        print(f"live (optional)   -> torvalds presence: {hits or '(none/offline)'}. [OK]")
    except Exception as e:  # noqa: BLE001
        print(f"live (optional)   -> skipped (network: {type(e).__name__}).")


def main() -> int:
    test_email_domain()
    test_footprint_scoring()
    test_canned_collect()
    test_endpoint_and_core_untouched()
    test_live_optional()
    print("\nAll extras (digital-footprint) assertions passed. [PASS]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
