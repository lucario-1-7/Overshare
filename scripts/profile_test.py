"""Extras: multi-post Pattern Engine + GitHub enrichment test.

Deterministic aggregation (synthetic posts), canned GitHub enrichment, and the
/extras/profile endpoint over real generated JPEGs — all runnable with no GPU.
Also re-asserts the core endpoints are unchanged.

    python -m scripts.profile_test
"""
from __future__ import annotations

import os
import sys
from io import BytesIO

from backend.contracts.signal import Signal
from backend.extras.collectors import enrich_github
from backend.extras.models import ProfileReport
from backend.extras.pattern import build_profile


def _s(t, v, src="presidio"):
    return Signal(type=t, value=v, source=src, confidence=0.9)


def test_pattern_engine() -> None:
    posts = [
        [_s("face", "face 1 of 1", "retinaface"), _s("employer", "Microsoft")],
        [_s("employer", "Microsoft"), _s("home_indicator", "bed", "yolo")],
        [_s("face", "face 1 of 1", "retinaface"), _s("employer", "Microsoft")],
        [_s("location", "Bangalore"), _s("face", "face 1 of 1", "retinaface")],
    ]
    r = build_profile(posts)
    assert r.totalPosts == 4
    assert r.signalFrequency.get("employer") == 3 and r.signalFrequency.get("face") == 3
    emp = [e for e in r.recurringEntities if e.type == "employer" and e.value == "Microsoft"]
    assert emp and emp[0].posts == 3
    assert r.exposureConsistency == 100  # every post has a sensitive type
    kinds = {i.kind for i in r.insights}
    assert "professional_identity" in kinds and "persistent_identity" in kinds
    assert "Microsoft" in next(i.label for i in r.insights if i.kind == "professional_identity")
    # determinism
    assert build_profile(posts).model_dump() == r.model_dump()
    print(f"pattern engine    -> {r.totalPosts} posts, consistency={r.exposureConsistency}%, "
          f"{len(r.recurringEntities)} recurring, {len(r.insights)} insights, trend={r.exposureTrend}. [OK]")


def test_empty_profile() -> None:
    r = build_profile([])
    assert r.totalPosts == 0 and r.insights == []
    print("empty profile     -> 0 posts -> empty report (no crash). [OK]")


def test_github_enrich_canned() -> None:
    os.environ["OVERSHARE_CANNED"] = "1"
    try:
        sigs = enrich_github("torvalds")
        assert any(s.type == "github_profile" for s in sigs)
        assert any(s.type == "location" and "Portland" in s.value for s in sigs)
    finally:
        os.environ.pop("OVERSHARE_CANNED", None)
    print("github enrich     -> canned torvalds -> profile + location signals. [OK]")


def test_profile_endpoint_and_core() -> None:
    from fastapi.testclient import TestClient
    from PIL import Image

    from backend.main import app
    from scripts.make_test_image import make_gps_jpeg

    def clean_jpeg() -> bytes:
        buf = BytesIO()
        Image.new("RGB", (64, 64), "white").save(buf, "JPEG")
        return buf.getvalue()

    files = [
        ("files", ("p1.jpg", make_gps_jpeg(), "image/jpeg")),
        ("files", ("p2.jpg", make_gps_jpeg(), "image/jpeg")),
        ("files", ("p3.jpg", clean_jpeg(), "image/jpeg")),
    ]
    with TestClient(app) as client:
        r = client.post("/extras/profile", files=files)
        assert r.status_code == 200, r.text
        rep = ProfileReport.model_validate(r.json())
        assert rep.totalPosts == 3
        assert rep.signalFrequency.get("gps", 0) == 2          # 2 GPS posts + 1 clean
        # CORE endpoints unchanged
        assert client.get("/health").status_code == 200
        assert client.post("/analyze", json={"text": "hi"}).status_code == 200
    print(f"/extras/profile   -> 3 uploads aggregated (gps in 2/3); core endpoints unchanged. [OK]")


def main() -> int:
    test_pattern_engine()
    test_empty_profile()
    test_github_enrich_canned()
    test_profile_endpoint_and_core()
    print("\nAll multi-post profile + enrichment assertions passed. [PASS]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
