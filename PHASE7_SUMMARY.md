# Overshare — Phase 7 Summary

> **Phase 7 goal (PLAN §4.11):** add the **only generative-AI layer** — a local
> **Ollama** model that turns the assembled Report into one plain-English `explanation`
> paragraph. Purely **additive and non-blocking**: if Ollama is down/slow/absent, the
> report ships without it. Never on the critical path (PLAN §10 cut-line #1).

**Status: complete, verified (graceful-degradation), on `main`.** ✅

---

## What was built

### 1. `backend/explain.py` (new) — the LLM layer
- **`generate_explanation(report) -> str | None`** — POSTs a grounded prompt to a local
  Ollama (`/api/generate`, `stream=False`) and returns one short paragraph.
- **`_prompt(report)`** — builds the prompt from **only what was detected**: the distinct
  signal types + values, the risk scores, and the attack path, with an explicit
  "do not invent any detail not listed" guard so the model stays grounded.
- **Local only** — talks to `localhost:11434`, so the "nothing leaves this machine"
  guarantee holds (no external model API in the critical path, PLAN §7).
- **Config via env:** `OLLAMA_HOST` (default `http://localhost:11434`), `OLLAMA_MODEL`
  (default `llama3.2`), `OLLAMA_TIMEOUT` (default 20s), `OVERSHARE_NO_LLM=1` to skip.

### 2. `backend/main.py` (2-line wire) — the integration seam
Called in `/analyze` **after** `build_report`, offloaded with `run_in_threadpool` so the
sync HTTP call can't block the event loop:
```python
report = build_report(signals, models_run, annotated_image)
report.explanation = await run_in_threadpool(generate_explanation, report)
```
Crucially this leaves **`build_report` pure** — every test that calls it (contract_check,
phase4_test) is unaffected, and the LLM only runs on the real request path.

### 3. `scripts/phase7_test.py` (new) — acceptance test
Pins the non-blocking contract **without needing Ollama**.

---

## Why it's safe (the non-blocking contract)
`generate_explanation` returns `None` — fast, never raising — on every failure mode:
- `OVERSHARE_NO_LLM=1` set,
- no signals (honest when clean — nothing to explain),
- `requests` not installed (light venv),
- Ollama unreachable (connection refused returns immediately),
- timeout, non-200, or malformed JSON.

So `report.explanation` is simply `null` and the report ships exactly as before. This is
the **highest-value AI-Integration stretch** (the one *generative* layer) that is never
load-bearing — drop it first if anything slips (PLAN §10).

---

## Verification

`python -m scripts.phase7_test` — **all assertions pass:**

| Check | Result |
|---|---|
| Prompt builder | grounded — includes facts (`ACME Corp`), risk scores, and a "don't invent" guard |
| `OVERSHARE_NO_LLM=1` | returns `None` |
| No signals | returns `None` (honest when clean) |
| Ollama unreachable (discard port, 2s) | returns `None` **fast, never raises** |
| `/analyze` with LLM disabled | still `200` + valid Report, `explanation = null` |

Regression: `contract_check`, `smoke_test`, and `phase4_test` all remain green —
Phase 7 added a new module and a 2-line wire; nothing else changed.

> **Live generation** (a real paragraph) is confirmed on a box running `ollama serve`
> with a pulled model — not required for the tests above, which prove the layer is safe
> whether or not Ollama exists.

---

## How to run (real explanation)

```bash
ollama serve &              # if not already running
ollama pull llama3.2        # or set OLLAMA_MODEL to a model you have
# uvicorn backend.main:app --port 8077
# POST /analyze with a rich photo/caption -> report.explanation now has the paragraph
```
Knobs: `OLLAMA_HOST`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT`, `OVERSHARE_NO_LLM=1`.

---

## What's next

Backend + frontend are complete (Phases 1·2·3·4·5·7). The remaining piece is
**Phase 6 — deploy / Cloudflare tunnel**: expose the local box over HTTPS so judges can
hit it from a phone (the Shippedness point + the public demo URL for the deck).
