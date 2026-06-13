r"""Contract gate for the Phase 3/4/5 split — run this anytime, in either venv.

Proves the shared interfaces hold so the three lanes integrate cleanly:
  1. fixtures/signals_sample.json  -> every entry is a valid Signal, and the set
     covers every SignalType the downstream phases rely on.
  2. fixtures/report_sample.json   -> a valid Report (the Phase 5 contract) that
     also survives a model_dump(mode="json") round-trip (what the API actually sends).
  3. the assembled-from-signals path produces a schema-valid Report (the Phase 4 seam),
     and the router degrades cleanly with no models (the Phase 3 seam).

Run:  .\.venv\Scripts\python.exe -m scripts.contract_check
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.assemble import build_report
from backend.contracts.report import Report
from backend.contracts.signal import Signal, SignalType
from backend.router import run_pipelines
from scripts.make_test_image import make_gps_jpeg

try:
    from typing import get_args
except ImportError:  # pragma: no cover
    get_args = None

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "fixtures"


def _load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def check_signal_fixture() -> list:
    raw = _load("signals_sample.json")
    signals = [Signal.model_validate(s) for s in raw]  # raises if any is invalid
    covered = {s.type for s in signals}
    all_types = set(get_args(SignalType)) if get_args else covered
    missing = all_types - covered
    print(f"signals_sample.json -> {len(signals)} valid Signals, "
          f"{len(covered)}/{len(all_types)} SignalTypes covered.")
    assert not missing, f"fixture is missing example signals for: {sorted(missing)}"
    return signals


def check_report_fixture() -> None:
    rep = Report.model_validate(_load("report_sample.json"))  # the Phase 5 contract
    payload = rep.model_dump(mode="json")
    json.dumps(payload)  # must be JSON-serializable (what /sample-report returns)
    assert payload["risks"].keys() == {"doxxing", "stalking", "phishing"}
    assert isinstance(payload["graph"]["nodes"], list) and payload["graph"]["nodes"]
    assert payload["attackPath"] and payload["fixes"]
    print(f"report_sample.json  -> valid Report; "
          f"{len(payload['graph']['nodes'])} graph nodes, "
          f"{len(payload['attackPath'])} attack steps, {len(payload['fixes'])} fixes.")


def check_assemble_seam(signals: list) -> None:
    # Phase 4 seam: assemble must produce a schema-valid Report from any signals[].
    rep = build_report(signals, ["exif", "yolo", "retinaface", "paddleocr", "presidio", "footprint"])
    rep.model_dump(mode="json")
    print("assemble seam       -> build_report(signals) returns a valid Report.")


def check_router_seam() -> None:
    # Phase 3 seam: with no models, the image path still runs EXIF and never crashes.
    sig, run = run_pipelines(image_bytes=make_gps_jpeg(), models={})
    assert "exif" in run and any(s.type == "gps" for s in sig)
    # text/username paths must not crash with no engines loaded.
    run_pipelines(text="lunch near MG Road", models={})
    run_pipelines(username="johndoe", models={})
    print("router seam         -> EXIF-only path + text/username stubs run clean.")


def check_sample_endpoint() -> None:
    # Phase 5 seam: GET /sample-report must return a valid Report over HTTP.
    from fastapi.testclient import TestClient

    from backend.main import app

    with TestClient(app) as client:
        r = client.get("/sample-report")
        assert r.status_code == 200, r.text
        Report.model_validate(r.json())  # the frontend's contract, served live
    print("sample endpoint     -> GET /sample-report returns a valid Report.")


def main() -> int:
    signals = check_signal_fixture()
    check_report_fixture()
    check_assemble_seam(signals)
    check_router_seam()
    check_sample_endpoint()
    print("\nAll contracts hold — Phase 3/4/5 lanes are safe to build in parallel. [PASS]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
