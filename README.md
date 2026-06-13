# Overshare

A **local multi-modal privacy-intelligence engine**. Drop a photo / screenshot / caption / username → it shows what a stranger could infer about you as an **exposure graph + risk scores + attack path + fixes**. See [PLAN.md](PLAN.md) for the full design.

Everything runs **on-device**: uploads are processed in-memory, never written to disk, no database, no external model API in the critical path.

---

## Status — Phase 1 complete (the spine + EXIF)

The connective tissue is live: `RAW INPUT → [perception] → signals[] → Report → UI`.

- **Frozen contracts** — `Signal` (PLAN §1) and `Report` (PLAN §4.12).
- **FastAPI `POST /analyze`** — one endpoint, accepts multipart (file) or JSON (text/username); models load once at startup.
- **EXIF pipeline** — real `gps` / `device` / `timestamp` extraction from image bytes.
- **Throwaway UI** — drag-drop a photo → see the raw Report JSON + signal chips.
- **In-memory only** — `meta.stored = false`.

Deferred to later phases: YOLO, RetinaFace, OCR→Presidio, Exposure Graph, Risk Engine, Attack Paths, Fixes, real React frontend, optional LLM.

---

## Run it (Windows)

```powershell
# one-time: create venv + install the light backend deps
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

# start the server
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8077
```

Then open <http://127.0.0.1:8077/> and drop a GPS-tagged photo.

### Verify the pipeline

```powershell
# end-to-end acceptance test (no server needed — uses TestClient)
.\.venv\Scripts\python.exe -m scripts.smoke_test

# or hit a running server
.\.venv\Scripts\python.exe -m scripts.live_check
```

---

## Layout

```
backend/
  main.py              FastAPI app + POST /analyze
  router.py            classify input → fire pipelines
  assemble.py          signals[] → Report
  contracts/
    signal.py          Signal (FROZEN)
    report.py          Report (FROZEN)
  pipelines/
    exif.py            EXIF → gps / device / timestamp
  requirements.txt     light Phase 1 deps
frontend/
  index.html           throwaway proof page (real React UI = Phase 5)
scripts/
  make_test_image.py   synthetic GPS / clean JPEGs
  smoke_test.py        Phase 1 acceptance test
  live_check.py        hit a running server
  download_weights.py  pre-pull ML weights (Phase 2+)
requirements-ml.txt    heavy ML stack (Phase 2+)
```

---

## Phase 2 prerequisite — Python version

The local interpreter is **Python 3.14**, which may not yet have wheels for
`torch` / `paddlepaddle`. Before Phase 2, create a dedicated **Python 3.11/3.12**
venv for the ML stack:

```powershell
py -3.11 -m venv .venv-ml
.\.venv-ml\Scripts\python.exe -m pip install -r requirements-ml.txt
.\.venv-ml\Scripts\python.exe -m scripts.download_weights
```
