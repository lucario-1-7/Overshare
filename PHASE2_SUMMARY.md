# Overshare — Phase 2 Summary

> **Phase 2 goal (PLAN hours 4–8):** add the perception models that produce
> bounding boxes — **YOLOv8 objects + RetinaFace faces + the Annotator** — turning
> the Phase 1 spine into a pipeline that *sees*. Everything still flows through the
> frozen `signals[]` contract; the intelligence layer (Phase 4) is untouched.

**Status: complete, verified on GPU, adversarially reviewed, and hardened.** ✅

---

## What was built

### 1. The ML environment — `.venv-ml` (the Phase 1 blocker, resolved)
Phase 1 flagged that the local interpreter (Python 3.14) has no torch/paddle wheels.
Resolved by standing up a dedicated **Python 3.11.9** venv with a **CUDA** stack:

- **torch 2.5.1+cu121 / torchvision 0.20.1+cu121** — verified `torch.cuda.is_available() == True`
  on the **NVIDIA RTX 4060 Laptop (8 GB)**.
- **ultralytics 8.4.66** (YOLOv8), **facexlib 0.3.0** (torch RetinaFace), plus the
  Phase 1 backend deps so the full server + tests run in one venv.
- numpy pinned to **2.x** (opencv 4.13 / scipy / numba in this stack are numpy-2-native;
  forcing `numpy<2` breaks the cv2 ABI — learned the hard way).

The light Phase-1 `.venv` still works (EXIF-only) — see graceful degradation below.

### 2. YOLOv8 object pipeline — `backend/pipelines/objects.py` (PLAN §4.4)
Stock COCO weights (`yolov8n`). Maps only **privacy-relevant** COCO classes to signals,
each with an `evidence.bbox` for the annotator:
- `person` → `person`
- `book` → `document` (COCO's nearest proxy; OCR reads it in Phase 3)
- bed / couch / chair / tv / laptop / cell phone / … → `home_indicator`

### 3. RetinaFace face pipeline — `backend/pipelines/faces.py` (PLAN §4.4)
Torch RetinaFace (resnet50) via facexlib → one `face` signal per face (with count),
each boxed. **Detection only — never recognition/matching** (the §4.4 ethics guard).

> **Backend deviation from the frozen `requirements-ml.txt`:** the plan named the
> TensorFlow `retina-face` package; we use facexlib's **PyTorch** RetinaFace instead.
> Reason: TensorFlow has no native-Windows GPU support (would run CPU-only and force
> a TF+torch coexistence), whereas facexlib keeps the whole perception stack on one
> framework on the GPU. The emitted contract (`source="retinaface"`, a `face` signal
> with a bbox) is byte-identical, so nothing downstream notices.

### 4. Annotator — `backend/annotator.py` (PLAN §4.6) — the "proof the AI is real" visual
PIL-only (works in both venvs). Reads every signal carrying `evidence.bbox`, draws a
labelled colour-coded box on a copy of the upload, returns a **base64 PNG** for
`report.annotatedImage`. No boxable signals → returns `None` (UI shows the raw upload).

### 5. Wiring + the two deferred Phase-1 hardening items
- **`main.py` lifespan** loads both models **once** onto the GPU (PLAN §4.2),
  import-guarded so a missing lib / failed load degrades to EXIF-only instead of
  crashing. `/health` now reports `device` + `cuda_available` + loaded models.
- **`router.py`** fires EXIF + YOLO + RetinaFace, injecting the loaded model handles.
- **Upload size cap (deferred from P1):** enforced **while streaming** the body
  (not just via `Content-Length`), closing the chunked-transfer bypass and the
  unbounded-JSON-body hole → `413`.
- **Threadpool offload (deferred from P1):** inference runs via `run_in_threadpool`
  so GPU work never blocks the event loop.

---

## Verification

`.\.venv-ml\Scripts\python.exe -m scripts.phase2_test` — **all assertions pass:**

| Check | Result |
|---|---|
| Annotator draws boxes (synthetic bbox signals) | valid PNG, size preserved, no-bbox signals ignored |
| Annotator honest-when-clean | `None` when nothing boxable / no image |
| Graceful degradation (no models) | image path still returns EXIF-only, no crash |
| Upload size cap | oversized body → `413`; normal upload still parses |
| **Concurrency burst** (6 differently-sized images at once) | all `200`, valid — shared-model lock holds |
| **Real photo on GPU** (`zidane.jpg`, end-to-end via `/analyze`) | `modelsRun=[exif,yolo,retinaface]`, detected `{person, face}`, annotated image present |

Light `.venv` (EXIF-only) and the Phase 1 smoke test both still pass — Phase 2 didn't
break the spine. A **live uvicorn** check (`scripts.live_check`) confirms the real
server boots, loads models on CUDA, and boxes a real photo. Visual spot-check of the
annotated output confirmed boxes land correctly (2 person + 2 face boxes, accurately placed).

---

## Adversarial review

An automated review (21 agents across 4 dimensions — contract conformance, ML-API
correctness, reliability/concurrency, annotator+wiring) surfaced **9 confirmed
findings**, each independently verified against the *actually-installed* library
source. **All 9 fixed.**

| # | Sev | Finding | Fix |
|---|---|---|---|
| 1 | high | RetinaFace `detect_faces` data race (shared per-image scale state) under the threadpool → silently mislocated boxes | per-model `threading.Lock` around inference |
| 2 | high | YOLO `predict` data race (shared cached predictor state) → wrong/mismatched results | per-model `threading.Lock` around inference |
| 3 | med | NaN detector score passes `_clamp01` → pydantic `ValidationError` → 500 (breaks "never raises") | NaN-safe clamp + try/except around each Signal build |
| 4 | med | Size cap bypassable via chunked transfer; JSON body uncapped → RAM DoS | enforce cap while streaming the body |
| 5 | low | `model.to(device)` failure silently swallowed + misleading log | log the failure; report actual device |
| 6 | low | Annotator label chip not clamped to right edge → truncated labels | clamp label x into the image |
| 7 | low | `/health` couldn't distinguish "models failed" from "intentionally EXIF-only" | added `cuda_available` |

---

## How to run

```powershell
# one-time: build the ML venv (Python 3.11) and install the CUDA stack
py -3.11 -m venv .venv-ml
.\.venv-ml\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
.\.venv-ml\Scripts\python.exe -m pip install ultralytics facexlib -r backend\requirements.txt
# (do NOT pin numpy<2 — opencv 4.13 needs numpy>=2)

# pre-pull weights (robust retry built in), then run the server
.\.venv-ml\Scripts\python.exe -m scripts.download_weights
.\.venv-ml\Scripts\python.exe -m uvicorn backend.main:app --port 8077
# open http://127.0.0.1:8077/ and drop a photo with a person/face
```

Verify: `.\.venv-ml\Scripts\python.exe -m scripts.phase2_test`

---

## What's next (Phase 3)

**PaddleOCR → Presidio** (PLAN hours 8–11): OCR the image for `screen_text`, chain it
(plus caption text) into Presidio + spaCy for `person_name` / `employer` / `email` /
`phone` / `location`. After that, `signals[]` is fully populated and the Phase 4
intelligence engines (Graph / Risk / Attack / Fix) can be built in parallel.

**Prerequisite:** `paddleocr` + `paddlepaddle`, `presidio-analyzer`/`-anonymizer`,
`spacy` + `en_core_web_lg` into `.venv-ml` (see `requirements-ml.txt`).
