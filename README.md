# Overshare

> **A local, multi-modal privacy-intelligence engine.** Drop a photo, screenshot,
> caption, or username and it shows what a stranger could infer about you — as an
> **exposure graph + risk scores + an attack-path narrative + one-click fixes**.

Built for **ARCNIGHT 2026 · CyberTech**. Everything runs **on-device**: uploads are
processed in memory, never written to disk, there is no database, and **no external
model API is in the critical path** (verifiable in the browser network tab).

---

## Why

People overshare without realizing how much a single post gives away. One casual
photo can leak your **home location** (EXIF GPS + a recognizable room), your
**employer and name** (a visible badge), your **contact info** (readable text), and
your **other accounts** (a reused handle). Overshare fuses these weak signals the way
an actual stranger would, and shows you the damage *before* you post — then helps you
fix it.

---

## The core idea — one contract connects everything

Every model, no matter what it looks at, emits the same tiny object: a **`Signal`**.
The "smart" half of the app never touches a photo or a model — it only ever reads a
flat `signals[]` list. That decoupling is the whole architecture:

```
RAW INPUT → [perception models] → signals[] → [graph + risk + attack + fixes] → Report → UI
                                      ▲
                       the single contract everything agrees on
```

```mermaid
flowchart LR
    UI[Frontend] -->|POST /analyze| API[FastAPI]
    API --> R{Router}
    R -->|image| IMG[EXIF · YOLO · RetinaFace · OCR]
    R -->|text| TXT[Presidio]
    R -->|username| FP[Footprint]
    IMG & TXT & FP --> SIG[(signals[])]
    SIG --> ANN[Annotator → boxed image]
    SIG --> GRAPH[Exposure Graph]
    SIG --> RISK[Risk Engine]
    SIG --> ATK[Attack Paths]
    SIG --> FIX[Fix Engine]
    ANN & GRAPH & RISK & ATK & FIX --> REP[Report JSON] --> UI
```

If you understand `signals[]`, you understand how every piece connects. The `Signal`
and `Report` schemas are **frozen** in [`backend/contracts/`](backend/contracts/) —
models can be added or swapped without the intelligence layer ever changing.

---

## Status

| Phase | Scope | State |
|---|---|---|
| **1 · Spine + EXIF** | Frozen contracts, FastAPI `/analyze`, EXIF (gps/device/timestamp), in-memory, throwaway UI | ✅ **Done** |
| **2 · Vision** | YOLOv8 objects, RetinaFace faces, the Annotator (boxed image), GPU model loading, size-cap + threadpool | ✅ **Done** |
| **3 · OCR + PII** | PaddleOCR → Presidio/spaCy (screen_text + person/employer/email/phone/location), footprint | 🟡 **Scaffolded** (stubs wired) |
| **4 · Intelligence** | Exposure Graph, Risk Engine, Attack-Path Generator, Fix Engine | 🟡 **Scaffolded** (stubs wired) |
| **5 · Frontend** | React + Tailwind + react-flow report UI | 🟡 **Scaffolded** (contract + fixtures) |
| **6 · Deploy** | Cloudflare tunnel (public HTTPS demo) | ⬜ Planned |
| **7 · Polish** | Optional local Ollama LLM `explanation` (non-blocking) | ⬜ Planned |

Phases 3–5 can be built **in parallel by three people** — see
[PHASE_HANDOFF.md](PHASE_HANDOFF.md).

---

## What works today (Phases 1–2)

- **`POST /analyze`** accepts a multipart image *or* JSON `{text, username}`.
- **EXIF** → `gps` (decimal lat/lon), `device`, `timestamp`.
- **YOLOv8** (stock COCO) → `person`, `home_indicator` (bed/sofa/tv/laptop/…), `document`.
- **RetinaFace** (torch) → `face` per face, **detection only, never recognition**.
- **Annotator** → draws labelled bounding boxes on the image, returned as base64 PNG.
- **Privacy by design** — `meta.stored = false`; bytes never hit disk.
- **Reliability first** — missing models degrade to EXIF-only instead of crashing;
  inference runs in a threadpool and is serialized per-model for correctness under load.

---

## Tech stack

- **Backend:** Python · FastAPI · Pydantic v2 · Uvicorn
- **Vision (GPU):** PyTorch (CUDA 12.1) · Ultralytics YOLOv8 · facexlib RetinaFace · Pillow
- **Text (Phase 3):** PaddleOCR (EasyOCR fallback) · Microsoft Presidio + spaCy · `requests`
- **Frontend (Phase 5):** React · Tailwind · react-flow
- **Optional LLM (Phase 7):** local Ollama — phrasing only, never load-bearing
- **Deploy (Phase 6):** Cloudflare Tunnel

---

## Quick start

The project uses **two virtual environments** so the backend can boot anywhere:

- **`.venv`** — light, instant boot, **EXIF-only** (no GPU/ML libs). Great for the
  spine, the intelligence layer (Phase 4), and the frontend (Phase 5).
- **`.venv-ml`** — **Python 3.11** + the CUDA ML stack. Needed for the vision models
  (Phase 2) and OCR/PII (Phase 3).

### Light backend (EXIF-only)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8077
```

### Full vision stack (GPU)

Requires an NVIDIA GPU + recent driver, and Python 3.11 (`py -3.11`).

```powershell
py -3.11 -m venv .venv-ml
# GPU PyTorch (CUDA 12.1) first, then the rest. Do NOT pin numpy<2 (opencv needs numpy>=2).
.\.venv-ml\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
.\.venv-ml\Scripts\python.exe -m pip install ultralytics facexlib -r backend\requirements.txt

# pre-pull model weights (robust retry built in), then run
.\.venv-ml\Scripts\python.exe -m scripts.download_weights
.\.venv-ml\Scripts\python.exe -m uvicorn backend.main:app --port 8077
```

Open <http://127.0.0.1:8077/> and drop a photo with a person/face (and ideally EXIF GPS).

---

## API

| Method · Path | Purpose |
|---|---|
| `POST /analyze` | Analyze a multipart image **or** JSON `{ "text": ..., "username": ... }` → a `Report`. |
| `GET /health` | `{ status, phase, device, cuda_available, models }`. |
| `GET /` | The throwaway proof UI (`frontend/index.html`). |
| `GET /sample-report` | A fully-populated example `Report` (for frontend dev — see fixtures). |

### The `Report` (the frontend's only contract — PLAN §4.12)

```jsonc
{
  "annotatedImage": "data:image/png;base64,...",   // boxed image, or null
  "signals":   [ { "type": "gps", "value": "12.97,77.59", "source": "exif",
                   "confidence": 0.99, "evidence": { "bbox": null, "text": "...", "raw": {} } } ],
  "graph":     { "nodes": [...], "edges": [...] },   // react-flow exposure graph
  "risks":     { "doxxing": 65, "stalking": 70, "phishing": 45 },
  "attackPath":[ "Employer identified…", "Profiles searched…", "…" ],
  "fixes":     [ { "issue": "EXIF GPS", "action": "Strip & re-download", "oneClick": true } ],
  "explanation": "optional LLM paragraph or null",
  "meta":      { "processedLocally": true, "stored": false, "modelsRun": ["exif","yolo","retinaface"] }
}
```

A live example is in [`fixtures/report_sample.json`](fixtures/report_sample.json) and at `GET /sample-report`.

---

## Testing

```powershell
# Contracts hold + fixtures valid (fast, no ML) — the shared parallel-build gate
.\.venv\Scripts\python.exe    -m scripts.contract_check

# Phase 1 spine (EXIF, serialization, honest-when-clean)
.\.venv\Scripts\python.exe    -m scripts.smoke_test

# Phase 2 vision on GPU (annotator, degradation, size-cap, concurrency, real detections)
.\.venv-ml\Scripts\python.exe -m scripts.phase2_test

# Hit a running server (EXIF + a real photo end-to-end)
.\.venv-ml\Scripts\python.exe -m scripts.live_check
```

---

## Project structure

```
backend/
  main.py                FastAPI app · POST /analyze · /health · /sample-report · model loading
  router.py              classify input → fire pipelines (EXIF/YOLO/RetinaFace/OCR→PII/footprint)
  assemble.py            signals[] → Report (calls the intelligence layer)
  annotator.py           draw labelled boxes from bbox signals → base64 PNG
  contracts/             ── FROZEN ──
    signal.py            Signal: type · value · source · confidence · evidence(bbox/text/raw)
    report.py            Report: annotatedImage · signals · graph · risks · attackPath · fixes · meta
  pipelines/
    exif.py              ✅ gps / device / timestamp
    objects.py           ✅ YOLOv8 → person / home_indicator / document
    faces.py             ✅ facexlib RetinaFace → face (detection only)
    ocr.py               🟡 Phase 3 — PaddleOCR → screen_text
    pii.py               🟡 Phase 3 — Presidio/spaCy → person_name/employer/email/phone/location
    footprint.py         🟡 Phase 3 — username existence checks
    loaders.py           🟡 Phase 3 — load OCR/PII models at startup
  intelligence/          🟡 Phase 4 (reads signals[] only)
    graph.py             Exposure Graph (the named innovation)
    risk.py              Risk Engine (deterministic matrix)
    attack.py            Attack-Path Generator (templates)
    fix.py               Fix Engine
    engine.py            aggregator (stable seam assemble.py calls)
frontend/
  index.html             throwaway proof page (real React UI = Phase 5, in a new web/ dir)
fixtures/
  signals_sample.json    15 signals — every SignalType (Phase 4 builds against this)
  report_sample.json     a fully-populated Report (Phase 5 builds against this)
scripts/
  contract_check.py      validates contracts + fixtures + seams (parallel-build gate)
  smoke_test.py          Phase 1 acceptance test
  phase2_test.py         Phase 2 acceptance test (light + GPU tiers)
  live_check.py          hit a running server
  make_test_image.py     synthetic GPS / clean JPEGs
  download_weights.py    pre-pull ML weights (robust retry)
requirements-ml.txt      the heavy ML stack
```

---

## Building Phases 3 · 4 · 5 in parallel

Because everything flows through the frozen contracts, three people can work at once
without colliding — the lanes edit **disjoint files**, and the seams between them are
pre-wired. Golden fixtures let each lane build before the others exist.

**Start here: [PHASE_HANDOFF.md](PHASE_HANDOFF.md)** — ownership map, per-phase
contracts, the branch-per-phase git workflow, and the acceptance gate.

```bash
git checkout main && git pull
git checkout -b feat/phase-3   # or feat/phase-4 / feat/phase-5
# work only in your lane; run scripts/contract_check.py before every PR
```

---

## Privacy & ethics

- **Nothing leaves the machine.** In-memory processing, no disk, no DB, no external
  model API in the critical path. `meta.stored = false` is shown in the UI.
- **Faces are detected, never recognized.** RetinaFace finds faces to box them; it
  does not match anyone against the web. "Face matched" appears only as a *hypothetical*
  step in the attack narrative — never something the tool performs.
- **Defensive intent.** Overshare exists to help people reduce their own exposure.

---

## Documentation

- **[PLAN.md](PLAN.md)** — the full design & connection map (the source of truth).
- **[PHASE1_SUMMARY.md](PHASE1_SUMMARY.md)** — spine + EXIF.
- **[PHASE2_SUMMARY.md](PHASE2_SUMMARY.md)** — vision perception (build, review, hardening).
- **[PHASE_HANDOFF.md](PHASE_HANDOFF.md)** — how to build Phases 3/4/5 in parallel.
