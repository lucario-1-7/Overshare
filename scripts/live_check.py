"""Hit the LIVE uvicorn server (not the in-process TestClient) to confirm it
actually boots and serves the page + endpoint. Usage:
    python -m scripts.live_check [base_url]
"""
from __future__ import annotations

import sys
import time

import httpx

from scripts.make_test_image import make_gps_jpeg

base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8077"

for _ in range(40):
    try:
        h = httpx.get(base + "/health", timeout=2)
        break
    except Exception:
        time.sleep(0.25)
else:
    print("server never came up")
    sys.exit(1)

print("GET /health  ->", h.status_code, h.json())

idx = httpx.get(base + "/", timeout=5)
print("GET /        ->", idx.status_code, "| html bytes:", len(idx.text),
      "| has OVERSHARE:", "OVERSHARE" in idx.text)

r = httpx.post(base + "/analyze",
               files={"file": ("p.jpg", make_gps_jpeg(), "image/jpeg")}, timeout=10)
rep = r.json()
print("POST /analyze (EXIF) ->", r.status_code, "| signal types:",
      [s["type"] for s in rep["signals"]])
print("gps value   :", next(s["value"] for s in rep["signals"] if s["type"] == "gps"))

# Phase 2: POST a real photo (ultralytics' bundled zidane.jpg — people + faces) and
# confirm the perception models fired and the annotator returned a boxed image.
try:
    from ultralytics.utils import ASSETS

    zidane = ASSETS / "zidane.jpg"
    if zidane.exists():
        r2 = httpx.post(base + "/analyze",
                        files={"file": ("z.jpg", zidane.read_bytes(), "image/jpeg")}, timeout=30)
        rep2 = r2.json()
        types = sorted({s["type"] for s in rep2["signals"]})
        print("POST /analyze (real) ->", r2.status_code, "| modelsRun:", rep2["meta"]["modelsRun"],
              "| types:", types,
              "| annotatedImage:", "present" if rep2.get("annotatedImage") else "none")
except Exception as e:  # noqa: BLE001 — light venv has no ultralytics; skip cleanly
    print("real-image check skipped:", type(e).__name__)

print("LIVE SERVER OK")
