# Overshare — Parallel Build Handoff (Phases 3 · 4 · 5)

Phases 1 & 2 are done and on `main` (EXIF + YOLO + RetinaFace + Annotator, verified on
GPU). This doc lets **three people build Phases 3, 4, and 5 at the same time** without
blocking or conflicting with each other.

## The one rule that makes this work

Everything flows through two frozen contracts in `backend/contracts/`:

```
RAW INPUT → [perception] → signals[] → [intelligence] → Report → UI
            (Phase 3)                   (Phase 4)                (Phase 5)
```

- **`Signal`** — every extractor emits these and appends to one list. (`signal.py`)
- **`Report`** — the only thing the frontend consumes. (`report.py`)

**Do not edit `backend/contracts/`.** It's frozen. Everything below plugs into it.
Because Phase 3 only *produces* signals, Phase 4 only *consumes* signals, and Phase 5
only *consumes* the Report, the three lanes touch disjoint files — so they merge clean.

---

## Ownership map — who edits what

| Lane | You OWN (edit freely) | You must NOT touch |
|---|---|---|
| **Phase 3** (perception/input) | `backend/pipelines/ocr.py`, `pii.py`, `footprint.py`, `loaders.py` | contracts, intelligence/, frontend, the other pipelines |
| **Phase 4** (intelligence) | `backend/intelligence/graph.py`, `risk.py`, `attack.py`, `fix.py` | contracts, pipelines/, frontend, `engine.py`/`assemble.py` |
| **Phase 5** (frontend) | a NEW `web/` dir (React + Tailwind + react-flow) | all of `backend/` |

**Already wired for you (stable seams — nobody needs to edit these):**
`router.py` calls the Phase 3 stubs · `main.py` lifespan calls `load_phase3_models` ·
`assemble.py` calls `intelligence/engine.py` · `engine.py` calls the four Phase 4 stubs.
Fill in the stub *bodies*; the wiring already routes your output into the Report.

> The stubs all return empty/default today, so `main` runs green right now
> (`scripts/phase2_test.py`, `scripts/contract_check.py`). Filling a stub just makes
> its part of the Report light up — no other file changes.

---

## Phase 3 — Perception & Input  (PLAN hours 8–11, §4.4)

**Goal:** add `screen_text` (OCR), PII (`person_name`/`employer`/`email`/`phone`/
`location`/`address`), and `username` (footprint) signals.

Implement the functions in your four files — each file's docstring is the full spec:
- `ocr.py`: `load_ocr_model(device)` + `extract_ocr_signals(image_bytes, model)` → `screen_text` (with bbox)
- `pii.py`: `load_pii_engine()` + `extract_pii_signals(text, engine)` → PII types (Presidio + spaCy)
- `footprint.py`: `extract_footprint_signals(username)` → `username`
- `loaders.py`: stash `models["ocr"]` / `models["pii"]` (called once at startup)

The OCR→PII chain is already wired in `router.py` (your OCR text is fed to your PII fn).
**Install:** `paddleocr` + `paddlepaddle`, `presidio-analyzer`/`-anonymizer`, `spacy`
+ `en_core_web_lg`, `requests` into `.venv-ml` (see `requirements-ml.txt`).
**Test in isolation:** unit-test each `extract_*` on a sample image/string; then run
the live server and POST a photo with text — your new signals appear in the report.
Match the existing pipelines: lazy heavy imports, never raise (return `[]`), `None`-skip.

## Phase 4 — Intelligence  (PLAN hours 11–17, §4.7–§4.10)

**Goal:** turn `signals[]` into `graph` / `risks` / `attackPath` / `fixes`.
You depend on NOTHING from Phase 3 — build against **`fixtures/signals_sample.json`**
(15 signals, every type). Implement the four pure functions (specs in each docstring):
- `graph.py`: `build_graph(signals) → Graph` (the named innovation; User-centred + fusion edges)
- `risk.py`: `score_risks(signals) → Risks` (the §4.8 matrix, clamp 0–100)
- `attack.py`: `build_attack_path(signals) → list[str]` (§4.9 templates)
- `fix.py`: `suggest_fixes(signals) → list[Fix]` (§4.10 mapping)

**Test in isolation, no server needed:**
```python
import json; from backend.contracts.signal import Signal
from backend.intelligence.engine import build_intelligence
sigs = [Signal.model_validate(s) for s in json.load(open("fixtures/signals_sample.json"))]
print(build_intelligence(sigs))   # graph/risks/attackPath/fixes light up as you implement
```
Deterministic only — same signal set → same output (demo-safe, no LLM).

## Phase 5 — Frontend  (PLAN hours 17–20, §4.1)

**Goal:** React + Tailwind app that renders a `Report` into fixed sections: Upload →
Annotated Image → Signal chips → **Exposure Graph (react-flow)** → Risk meters →
Attack Path → Fixes → Explanation. (`frontend/index.html` is a throwaway proof — replace it.)

You depend on NOTHING from Phase 3/4 — develop against the **`Report` contract**:
- **`fixtures/report_sample.json`** — a fully-populated Report (import it directly), or
- **`GET /sample-report`** on the running server — returns that same fixture over HTTP, or
- **`POST /analyze`** with an image — real Phases 1+2 output (signals + annotated image;
  graph/risks stay empty until Phase 4 lands, which is fine — your UI handles empties).

Treat every field as optional-friendly: `annotatedImage` may be `null`, `graph` may be empty.
Use react-flow/cytoscape for the graph (don't hand-roll). All intelligence is server-side.

---

## Git workflow (3 people, conflict-free)

```bash
git checkout main && git pull            # everyone starts from Phases 1+2 + this scaffolding
git checkout -b feat/phase-3             # (or feat/phase-4, feat/phase-5)
# ...work only in your lane's files...
git push -u origin feat/phase-3          # open a PR into main
```
Because the lanes edit disjoint files, PRs merge without conflicts. Shared files
(`router.py`, `assemble.py`, `engine.py`, `main.py`) are already wired — leave them be;
if you genuinely must change a seam, ping the group so it's a deliberate, single edit.

`requirements-ml.txt` is the one file Phase 3 appends to — add deps at the end only.

## Acceptance gate (run before every PR)

```powershell
.\.venv\Scripts\python.exe    -m scripts.contract_check   # contracts still hold (fast, no ML)
.\.venv\Scripts\python.exe    -m scripts.smoke_test        # Phase 1 spine intact
.\.venv-ml\Scripts\python.exe -m scripts.phase2_test       # Phase 2 vision intact (GPU)
```
All three must stay green. `contract_check.py` is the shared guard that the seams and
fixtures still line up — if it passes, your lane integrates with the others.

## Integration (after the three PRs merge)

A photo with a face + badge + caption + handle should yield: signals from all
extractors → a populated exposure graph + non-zero risk meters + an attack path +
fixes → rendered by the React UI. Then Phase 6 (deploy/tunnel) and the optional
Phase 7 LLM `explanation`.
