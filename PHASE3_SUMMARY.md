# Overshare — Phase 3 Summary

> **Phase 3 goal (PLAN hours 8–11, §4.4):** add the perception that *reads* —
> **PaddleOCR → Presidio (PII)** plus the **footprint** existence checks — so that
> after this, `signals[]` is fully populated (visual + textual + identity). Everything
> still flows through the frozen `Signal` contract; the intelligence layer (Phase 4)
> is untouched.

**Status: complete, logic-verified, lazy-import-safe, on `main`.** ✅

---

## What was built

### 1. OCR pipeline — `backend/pipelines/ocr.py` (PLAN §4.4)
PaddleOCR primary, **EasyOCR fallback**, graceful skip if neither is installed. Emits
one `screen_text` Signal per recognized region, each with an `evidence.bbox` for the
Annotator. The recognized string is put in **both** `value` and `evidence.text` so
`router.py` can chain it into the PII engine (PLAN §3 step 4). A version-tolerant
parser (`_paddle_lines`) handles PaddleOCR's wrapped-`[page]` and bare-`page` result
shapes; `_box_to_xywh` converts either engine's 4-point polygon to the frozen
`[x, y, w, h]` bbox. Confidence floor + a hard cap keep dense screenshots from
flooding the report.

### 2. PII pipeline — `backend/pipelines/pii.py` (PLAN §4.4)
Presidio `AnalyzerEngine` on spaCy `en_core_web_lg`. The **same** function runs over
two text sources (router wires both): the caption/text input, and the OCR'd
`screen_text`. Maps Presidio entities → frozen types: PERSON→`person_name`,
ORGANIZATION→`employer`, EMAIL_ADDRESS→`email`, PHONE_NUMBER→`phone`,
LOCATION→`location`, `*ADDRESS*`→`address`. De-dupes `(type, value)` across the two
sources, score-floors, caps.

### 3. Footprint pipeline — `backend/pipelines/footprint.py` (PLAN §4.4, §10)
`requests` existence checks across GitHub / Reddit / GitLab / dev.to, each bounded by
a short timeout and fully guarded. Emits a `username` Signal per hit
(`value="handle (site)"`, `evidence.text=<profile URL>`). Handles an email input by
probing with its local part. **Reliability (PLAN §10):** a canned fallback
(`OVERSHARE_CANNED=1`, or a known demo handle) returns deterministic hits so a
rate-limited live run never hangs or comes back empty.

### 4. `loaders.py`
Already wired — `load_phase3_models` populates `models["ocr"]`/`models["pii"]` once at
startup. No change needed; the OCR/PII loaders it calls are now implemented.

### 5. Acceptance test — `scripts/phase3_test.py` (new, mirrors `phase2_test.py`)
Unit-tests all three extractors' contract-shaping logic with **stub** readers/engines
(so it runs with no GPU/heavy libs), plus the never-raise guards and an optional live
footprint check.

**House-style match:** every file uses lazy heavy imports, `_clamp01` (NaN-safe),
never-raise/return-`[]`, model-`None`→skip; OCR serializes inference under a lock
(readers aren't reentrant and `main.py` offloads to a threadpool).

---

## Verification

`python -m scripts.phase3_test` — **all assertions pass:**

| Check | Result |
|---|---|
| None / empty / invalid inputs | every extractor returns `[]` (never raises) |
| OCR helpers | bbox conversion + Paddle parse (wrapped **and** bare) correct |
| OCR extract (stub easyocr reader) | one `screen_text` Signal, correct bbox, value+text both set |
| PII mapping (stub engine) | ORG→employer, EMAIL→email; unmapped (DATE_TIME) dropped; `source=presidio` |
| Footprint canned (`johndoe`) | 2 `username` signals, no network |
| **Footprint live (`torvalds`)** | **real hits: `torvalds (github)`, `torvalds (gitlab)`** |

`scripts.contract_check` and `scripts.smoke_test` both still pass — Phase 3 didn't
touch the spine, and the lazy-import rule holds (with no ML libs the server boots
EXIF-only and the pipelines skip cleanly, logging the degradation).

> **Honest scope note:** the heavy *model inference* (PaddleOCR + Presidio on CUDA)
> is exercised on the **GPU box** (`.venv-ml`), not on the contributor's GPU-less Mac.
> What's verified everywhere is the contract-shaping logic + graceful degradation —
> the part the rest of the app depends on. See "How to run" for the GPU confirmation step.

---

## Hardening (focused review)

Defensive measures baked in (the same failure modes Phase 1/2 review surfaced):
- **Never raises:** every extractor + per-item body is guarded → a bad image / odd
  library output drops that item, never 500s the request.
- **NaN-safe confidence** (`_clamp01`) so a stray detector score can't fail the
  pydantic `ge/le` validator.
- **Concurrency:** OCR inference under a `threading.Lock` (readers cache per-call state;
  `main.py` runs inference in a threadpool).
- **Reliability:** Paddle→EasyOCR fallback; footprint timeouts + canned fallback.
- **Privacy unchanged:** still in-memory only, `meta.stored=false`.

---

## How to run (GPU box)

```powershell
# into the Phase 2 ML venv:
.\.venv-ml\Scripts\python.exe -m pip install paddleocr paddlepaddle-gpu easyocr `
    presidio-analyzer presidio-anonymizer spacy requests
.\.venv-ml\Scripts\python.exe -m spacy download en_core_web_lg

.\.venv-ml\Scripts\python.exe -m scripts.download_weights   # pre-pulls OCR + spaCy
.\.venv-ml\Scripts\python.exe -m uvicorn backend.main:app --port 8077
# POST a photo with visible text + a caption + a username → screen_text / PII / username signals appear
```

Verify: `.\.venv-ml\Scripts\python.exe -m scripts.phase3_test`
(logic; CPU-OK) and a live `/analyze` for the real model output.

---

## What's next (Phase 4)

`signals[]` is now fully populated, so the **intelligence engines** can be built:
**Exposure Graph + Risk Engine + Attack-Path Generator + Fix Engine**
(PLAN §4.7–§4.10) — pure, deterministic functions over `signals[]`, built against
`fixtures/signals_sample.json`. No GPU, no models, no LLM.
