# Overshare — Phase 1 Summary

> **Phase 1 goal (PLAN §6 critical path):** prove the whole pipeline end-to-end with
> the cheapest model first — *Contracts → API → EXIF → `signals[]` → Report → UI*.
> Everything downstream (graph, risk, attack, fixes, LLM) builds on this spine.

**Status: complete, verified, and hardened.** ✅

---

## What was built

### 1. The frozen contracts — the keystone (PLAN §1, §4.12)
Every extractor emits the same tiny object — a **Signal** — and everything downstream
reads only `signals[]`. Freezing this in Phase 1 is what lets later phases add/remove
models without touching the intelligence layer.

- **`backend/contracts/signal.py`** — `Signal { type, value, source, confidence, evidence }`
  with `Evidence { bbox, text, raw }`. `type`/`source` are typed enums covering every
  signal the plan defines.
- **`backend/contracts/report.py`** — the frontend's only interface: `annotatedImage`,
  `signals`, `graph`, `risks`, `attackPath`, `fixes`, `explanation`, `meta`.

### 2. FastAPI `POST /analyze` (PLAN §4.2)
- **`backend/main.py`** — single endpoint, accepts **multipart** (file) *or* **JSON**
  (text/username). A **lifespan** hook is the one place models load (once, never
  per-request) — empty in Phase 1, ready for the GPU models in Phase 2.
- **In-memory only:** uploaded bytes are never written to disk; `meta.stored = false`.
  "Nothing left this machine" is the privacy differentiator, baked in from hour 0.

### 3. Input router + EXIF pipeline (PLAN §3, §4.3, §4.4)
- **`backend/router.py`** — classifies the payload and fires the right pipelines,
  appending Signals to one shared list. Phase 1: image → EXIF live; text/username stubbed.
- **`backend/pipelines/exif.py`** — Pillow-based EXIF reader emitting real
  `gps` (decimal lat/lon), `device` (make/model), and `timestamp` signals.
  Robust: any missing/garbled tag is skipped, never raised; a clean image yields zero
  signals ("honest when clean").
- **`backend/assemble.py`** — turns `signals[]` into a schema-valid Report (graph/risk/
  attack/fix default to valid-but-empty; later phases fill them in).

### 4. Throwaway proof UI
- **`frontend/index.html`** — drag-drop a photo → POST `/analyze` → renders signal chips,
  meta flags, and the raw Report JSON. Zero build step. The real React + Tailwind UI is
  Phase 5.

### 5. Tests + groundwork
- **`scripts/make_test_image.py`** — generates synthetic GPS / clean JPEGs.
- **`scripts/smoke_test.py`** — the Phase 1 acceptance test (via FastAPI TestClient).
- **`scripts/live_check.py`** — hits a running uvicorn server.
- **`scripts/download_weights.py`** + **`requirements-ml.txt`** — pre-pull the Phase 2+
  ML weights (import-guarded so it's safe to run before the heavy stack is installed).

---

## Verification

`python -m scripts.smoke_test` — **all assertions pass:**

| Check | Result |
|---|---|
| GPS photo → `gps` signal | `12.9716,77.5946` (decimal, signed correctly) |
| + `device` / `timestamp` | `TestCam Pixel-Sim` / `2024:01:15 14:30:00` |
| Clean image → 0 signals | valid empty Report |
| JSON text path | valid empty Report, no crash |
| `meta.stored` / `processedLocally` | `false` / `true` |
| Serialization hardening | non-JSON-safe `evidence.raw` coerced safely |
| Live server `/health`, `/`, `/analyze` | all `200`; lifespan startup fires clean |

---

## Adversarial review

An automated review (18 agents across 4 dimensions — contracts-vs-plan, EXIF
correctness, API robustness, privacy/security) surfaced 14 raw findings; each was
independently verified. **6 confirmed real, 0 were live Phase-1 bugs** (the only
shipping extractor, EXIF, emits JSON-safe values). Spine-level items were fixed anyway;
genuinely Phase-2-natural items were deferred with in-code markers.

| # | Finding | Action |
|---|---|---|
| 1 | `@app.on_event` deprecated in FastAPI 0.136 | **Fixed** → lifespan handler |
| 2 | `model_dump()` could 500 on non-JSON `evidence.raw` | **Fixed** → `_json_safe` validator on the frozen contract + `mode="json"` |
| 3 | DMS seconds could round to 6000 in test fixtures | **Fixed** → carry into minutes |
| 4 | `piexif` comment overstated its runtime role | **Fixed** → reworded |
| 5 | No upload size cap (OOM risk) | **Deferred** → in-code marker at the call site |
| 6 | Sync Pillow decode on the event loop | **Deferred** → in-code marker (offload when heavyweight models land) |

---

## How to run

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8077
# open http://127.0.0.1:8077/  and drop a GPS-tagged photo
```

Verify: `.\.venv\Scripts\python.exe -m scripts.smoke_test`

---

## What's next (Phase 2)

YOLOv8 + RetinaFace + the Annotator (bounding boxes on the image) — PLAN hours 4–8.

**Prerequisite:** the local interpreter is **Python 3.14**, which has no `torch` /
`paddlepaddle` wheels yet. The ML stack will need a dedicated **Python 3.11/3.12** venv
(`.venv-ml`) — see `requirements-ml.txt`.
