"""Phase 7 acceptance test — optional Ollama explanation.

Verifies the NON-BLOCKING contract without needing Ollama: the prompt is grounded,
the layer skips cleanly when disabled / no signals / Ollama unreachable, and /analyze
still ships a valid Report with the LLM off. (Live generation is verified separately
on a box running `ollama serve`.)

    python -m scripts.phase7_test
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from backend.contracts.report import Report
from backend.explain import _prompt, generate_explanation

ROOT = Path(__file__).resolve().parent.parent


def _report() -> Report:
    raw = json.loads((ROOT / "fixtures" / "report_sample.json").read_text(encoding="utf-8"))
    return Report.model_validate(raw)


def test_prompt_grounded() -> None:
    p = _prompt(_report())
    assert "doxxing" in p and "ACME Corp" in p and "you" in p.lower()
    assert "do not invent" in p.lower()  # grounding guard present
    print("prompt builder    -> grounded prompt (facts + risk scores + no-invent guard). [OK]")


def test_disabled_flag() -> None:
    os.environ["OVERSHARE_NO_LLM"] = "1"
    try:
        assert generate_explanation(_report()) is None
    finally:
        os.environ.pop("OVERSHARE_NO_LLM", None)
    print("disabled flag     -> OVERSHARE_NO_LLM=1 -> None. [OK]")


def test_honest_when_clean() -> None:
    assert generate_explanation(Report()) is None  # no signals -> nothing to explain
    print("honest when clean -> no signals -> None. [OK]")


def test_unreachable_is_graceful() -> None:
    os.environ["OLLAMA_HOST"] = "http://127.0.0.1:9"   # discard port -> connection refused
    os.environ["OLLAMA_TIMEOUT"] = "2"
    try:
        assert generate_explanation(_report()) is None  # must return None, never raise
    finally:
        os.environ.pop("OLLAMA_HOST", None)
        os.environ.pop("OLLAMA_TIMEOUT", None)
    print("unreachable Ollama-> None fast, never raises. [OK]")


def test_analyze_ships_without_llm() -> None:
    from fastapi.testclient import TestClient

    from backend.main import app

    os.environ["OVERSHARE_NO_LLM"] = "1"
    try:
        with TestClient(app) as client:
            r = client.post("/analyze", json={"text": "I work at ACME, email a@b.com"})
            assert r.status_code == 200, r.text
            rep = Report.model_validate(r.json())          # valid Report
            assert rep.explanation is None                  # LLM off -> field stays null
    finally:
        os.environ.pop("OVERSHARE_NO_LLM", None)
    print("/analyze          -> still 200 + valid Report with LLM disabled. [OK]")


def main() -> int:
    test_prompt_grounded()
    test_disabled_flag()
    test_honest_when_clean()
    test_unreachable_is_graceful()
    test_analyze_ships_without_llm()
    print("\nAll Phase 7 (LLM explanation) assertions passed. [PASS]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
