"""Phase 1 acceptance test — proves the spine end-to-end (PLAN §6 critical path).

Uses FastAPI's TestClient so no separate server process is needed. Run from the
repo root:   python -m scripts.smoke_test
"""
from __future__ import annotations

import json
import sys

from fastapi.testclient import TestClient

from backend.assemble import build_report
from backend.contracts.signal import Evidence, Signal
from backend.main import app
from scripts.make_test_image import make_clean_jpeg, make_gps_jpeg

client = TestClient(app)


def test_serialization_hardening() -> None:
    """The frozen contract must stay JSON-serializable even when a (future)
    extractor stuffs non-JSON-safe objects into evidence.raw."""

    class _Weird:  # stand-in for an IFDRational / numpy scalar / tensor
        def __float__(self):
            return 1.5

    sig = Signal(
        type="screen_text",
        value="x",
        source="paddleocr",
        confidence=0.5,
        evidence=Evidence(raw={"rational": _Weird(), "blob": b"\x00\xff", "nested": [b"a"]}),
    )
    rep = build_report([sig], ["paddleocr"])
    payload = rep.model_dump(mode="json")
    json.dumps(payload)  # would raise if anything slipped through
    coerced = payload["signals"][0]["evidence"]["raw"]
    assert coerced["rational"] == 1.5, coerced
    assert isinstance(coerced["blob"], str), coerced
    print("Serialization hardening -> non-JSON-safe evidence.raw coerced. [OK]")


def _post_image(b: bytes):
    return client.post("/analyze", files={"file": ("photo.jpg", b, "image/jpeg")})


def main() -> int:
    # 1) GPS-tagged image -> real gps/device/timestamp signals
    r = _post_image(make_gps_jpeg())
    assert r.status_code == 200, r.text
    rep = r.json()
    print("--- GPS image report ---")
    print(json.dumps(rep, indent=2))
    types = [s["type"] for s in rep["signals"]]
    assert "gps" in types, f"expected a gps signal, got {types}"
    assert "device" in types, f"expected a device signal, got {types}"
    assert "timestamp" in types, f"expected a timestamp signal, got {types}"
    assert rep["meta"]["stored"] is False, "meta.stored must be False"
    assert rep["meta"]["processedLocally"] is True
    assert "exif" in rep["meta"]["modelsRun"]

    gps = next(s for s in rep["signals"] if s["type"] == "gps")
    lat, lon = (float(x) for x in gps["value"].split(","))
    assert abs(lat - 12.9716) < 0.01, f"lat off: {lat}"
    assert abs(lon - 77.5946) < 0.01, f"lon off: {lon}"
    print(f"\nGPS decoded: lat={lat}, lon={lon}  (confidence={gps['confidence']})")

    # 2) clean image -> valid Report, zero signals ("honest when clean")
    r2 = _post_image(make_clean_jpeg())
    assert r2.status_code == 200, r2.text
    rep2 = r2.json()
    assert rep2["signals"] == [], f"clean image should yield no signals: {rep2['signals']}"
    # full report shape must still be valid/empty
    assert rep2["graph"] == {"nodes": [], "edges": []}
    assert rep2["risks"] == {"doxxing": 0, "stalking": 0, "phishing": 0}
    assert rep2["attackPath"] == [] and rep2["fixes"] == []
    print("\nClean image -> 0 signals, valid empty report. [OK]")

    # 3) JSON text path -> valid (empty in Phase 1) report, no crash
    r3 = client.post("/analyze", json={"text": "had lunch near MG Road"})
    assert r3.status_code == 200, r3.text
    assert r3.json()["signals"] == []
    print("JSON text path -> valid empty report (Phase 3 will populate). [OK]")

    # 4) frozen-contract serialization hardening
    test_serialization_hardening()

    print("\nAll Phase 1 assertions passed. [PASS]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
