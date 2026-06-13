"""Phase 3 acceptance test — OCR / PII / footprint extractors.

Unit-tests the three Phase 3 extractors' LOGIC without the heavy GPU models
(stub readers/engines stand in for PaddleOCR/Presidio), plus the never-raise
guards and an optional live footprint check. Runs in either venv:

    python -m scripts.phase3_test

The real model inference (PaddleOCR + Presidio on GPU) is exercised separately
on the ML box via the live server; this test pins the contract-shaping logic that
sits between the models and signals[] — which is what the rest of the app depends on.
"""
from __future__ import annotations

import sys
import types

from backend.pipelines.ocr import _box_to_xywh, _paddle_lines, extract_ocr_signals
from backend.pipelines.pii import _map_type, extract_pii_signals
from backend.pipelines.footprint import extract_footprint_signals


def _png_bytes() -> bytes:
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (140, 60), "white").save(buf, "PNG")
    return buf.getvalue()


def test_guards() -> None:
    assert extract_ocr_signals(b"", None) == []
    assert extract_ocr_signals(b"x", None) == []          # model None -> []
    assert extract_pii_signals("hello", None) == []       # engine None -> []
    assert extract_pii_signals("", object()) == []        # empty text -> []
    assert extract_footprint_signals("") == []            # empty handle -> []
    assert extract_footprint_signals("bad handle!!") == []  # invalid charset -> []
    print("guards            -> None/empty/invalid inputs return [] (never raise). [OK]")


def test_ocr_helpers() -> None:
    assert _box_to_xywh([[10, 10], [110, 10], [110, 50], [10, 50]]) == [10.0, 10.0, 100.0, 40.0]
    entry = [[[0, 0], [20, 0], [20, 10], [0, 10]], ("Hi", 0.9)]
    for result in ([[entry]], [entry]):  # PaddleOCR wrapped `[page]` AND bare `page`
        lines = _paddle_lines(result)
        assert lines and lines[0][1] == "Hi" and abs(lines[0][2] - 0.9) < 1e-6, result
    print("ocr helpers       -> bbox conversion + paddle parse (wrapped & bare). [OK]")


def test_ocr_extract() -> None:
    try:
        import numpy  # noqa: F401
    except Exception:
        print("ocr extract       -> skipped (numpy not installed).")
        return

    class StubReader:  # mimics easyocr.Reader.readtext
        def readtext(self, img):
            return [([[10, 10], [110, 10], [110, 40], [10, 40]], "ACME LOGIN", 0.92)]

    sigs = extract_ocr_signals(_png_bytes(), {"kind": "easyocr", "reader": StubReader()})
    assert len(sigs) == 1, sigs
    s = sigs[0]
    assert s.type == "screen_text" and s.source == "easyocr" and s.value == "ACME LOGIN"
    assert s.evidence and s.evidence.bbox == [10.0, 10.0, 100.0, 30.0]
    assert s.evidence.text == "ACME LOGIN"  # value+text both set so router can chain it
    print("ocr extract       -> stub reader -> screen_text Signal with bbox. [OK]")


def test_pii_mapping() -> None:
    assert _map_type("PERSON") == "person_name"
    assert _map_type("ORGANIZATION") == "employer"
    assert _map_type("EMAIL_ADDRESS") == "email"
    assert _map_type("PHONE_NUMBER") == "phone"
    assert _map_type("LOCATION") == "location"
    assert _map_type("STREET_ADDRESS") == "address"
    assert _map_type("DATE_TIME") is None  # unmapped -> ignored

    text = "I work at Microsoft and my email is john@acme.com"
    R = types.SimpleNamespace
    results = [
        R(entity_type="ORGANIZATION", start=text.index("Microsoft"),
          end=text.index("Microsoft") + len("Microsoft"), score=0.85),
        R(entity_type="EMAIL_ADDRESS", start=text.index("john@acme.com"),
          end=text.index("john@acme.com") + len("john@acme.com"), score=0.99),
        R(entity_type="DATE_TIME", start=0, end=1, score=0.99),  # must be dropped
    ]

    class StubEngine:  # mimics presidio AnalyzerEngine.analyze
        def analyze(self, text, language, entities=None):
            return results

    sigs = extract_pii_signals(text, StubEngine())
    by_type = {s.type: s.value for s in sigs}
    assert by_type.get("employer") == "Microsoft", by_type
    assert by_type.get("email") == "john@acme.com", by_type
    assert "DATE_TIME" not in [s.type for s in sigs]
    assert all(s.source == "presidio" for s in sigs)
    print("pii               -> entity->type mapping + Signal build (stub engine). [OK]")


def test_footprint_canned() -> None:
    sigs = extract_footprint_signals("johndoe")  # known canned demo handle (no network)
    assert sigs and all(s.type == "username" and s.source == "footprint" for s in sigs)
    assert any("github" in s.value for s in sigs)
    print(f"footprint canned  -> {len(sigs)} username signals for 'johndoe'. [OK]")


def test_footprint_live() -> None:
    try:
        import requests  # noqa: F401
    except Exception:
        print("footprint live    -> skipped (requests not installed).")
        return
    try:
        sigs = extract_footprint_signals("torvalds")  # a real GitHub user
    except Exception as e:  # noqa: BLE001
        print(f"footprint live    -> skipped (network: {type(e).__name__}).")
        return
    hits = [s.value for s in sigs]
    if any("github" in h for h in hits):
        print(f"footprint live    -> real hit(s): {hits}. [OK]")
    else:
        print("footprint live    -> no hits (offline/rate-limited); guards held. [OK]")


def main() -> int:
    test_guards()
    test_ocr_helpers()
    test_ocr_extract()
    test_pii_mapping()
    test_footprint_canned()
    test_footprint_live()
    print("\nAll Phase 3 logic assertions passed. [PASS]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
