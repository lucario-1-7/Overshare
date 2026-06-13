# Overshare — Phase 4 Summary

> **Phase 4 goal (PLAN hours 11–17, §4.7–§4.10):** turn the now-fully-populated
> `signals[]` into the **intelligence** the user actually sees — an Exposure Graph,
> Risk scores, an Attack Path, and Fixes. Four pure, deterministic functions over
> `signals[]`; **no GPU, no models, no LLM.** Consumes only the frozen contract, so it
> was built in parallel with Phases 3 & 5.

**Status: complete, verified, deterministic, on `main`.** ✅

---

## What was built

### 1. Exposure Graph — `backend/intelligence/graph.py` (PLAN §4.7) — the named innovation
Turns the set of present signal types into a graph centred on a `User` node for the
react-flow UI. Each exposure-worthy type becomes a child node (`Face Visible`,
`Employer: …`, `Username: …`, …) with a `user → node` "is exposed via" edge. The key
idea — **fusion nodes** that show combined signals are worse than the sum:
- **`home_locatable`** (type `fusion`) when `gps` + `home_indicator` are both present,
- **`identity_linkable`** (type `fusion`) when `face` + `username` are both present.

Node ids mirror `fixtures/report_sample.json` so the Phase 5 UI renders real output
identically. Deterministic ordering → same signals produce the same graph every time.

### 2. Risk Engine — `backend/intelligence/risk.py` (PLAN §4.8)
Deterministic rules over the *set* of signal types → `{doxxing, stalking, phishing}`,
each clamped to 0–100. The §4.8 connection matrix verbatim:

| Signals present | Doxxing | Stalking | Phishing |
|---|---|---|---|
| `gps` + `face` | — | +30 | — |
| `gps` + `face` + `home_indicator` | +40 | +20 | — |
| `employer` + (`email`\|`person_name`) | — | — | +25 |
| `location` + `username` | — | +20 | — |
| `email`\|`phone` | +10 | — | +20 |
| `face` + `username` | +15 | — | — |

Deterministic = demo-safe (same input → same score) and explainable.

### 3. Attack-Path Generator — `backend/intelligence/attack.py` (PLAN §4.9)
Matches the present signal set against templates (highest-signal first) → an ordered,
human-readable narrative, **parametrized** with the real values (employer, username,
contact). Ethics guard: recon steps describe what an attacker *would* do; the harmful
endpoint stays **hypothetical** ("…becomes possible") — the tool never performs it.
Templates: `face+employer+username` (5 steps), `gps+home_indicator+face` (3),
`location+timestamp` (2); `[]` if nothing matches.

### 4. Fix Engine — `backend/intelligence/fix.py` (PLAN §4.10)
Maps each **present** risky type to a concrete `Fix(issue, action, oneClick)`, de-duped
by issue. The **one-click EXIF-GPS strip** is the demo closer; everything else is a
manual guide. Wording/order mirror `report_sample.json`.

### 5. Acceptance test — `scripts/phase4_test.py` (new, mirrors phase2/3_test)
Runs `build_intelligence` over `fixtures/signals_sample.json` and pins every output.

> `backend/intelligence/engine.py` (the `assemble.py` seam) was already wired and is
> untouched — it wraps each engine in try/except so one failing engine degrades to its
> empty default instead of failing the request (reliability first).

---

## Verification

`python -m scripts.phase4_test` — **all assertions pass:**

| Check | Result |
|---|---|
| Risk matrix on the 15-signal fixture | `doxxing=65, stalking=70, phishing=45` — **matches `report_sample.json` exactly** |
| Exposure graph | 13 nodes / 16 edges, `user` hub, both fusion nodes present, every edge points at a real node |
| Attack path | 5 steps (face+employer+username template), parametrized (`ACME Corp`, `johndoe`), hypothetical endpoint |
| Fix engine | 6 fixes, exactly 1 one-click (EXIF GPS), de-duped |
| Empty input (honest when clean) | risks all 0, attackPath `[]`, fixes `[]`, graph = just the `user` node |
| Determinism | same signals → byte-identical graph dump |

`scripts.contract_check` passes (full `signals → intelligence → Report` integration),
and `phase3_test` + `smoke_test` remain green — Phase 4 touched only `intelligence/`.

---

## Hardening / review (focused)
- **Deterministic by design** — no randomness, no model, no LLM → demo-safe and explainable.
- **Defensive value extraction** — graph label builders are guarded (fall back to the
  type name) so an odd `value` can't break graph construction.
- **Reliability** — `engine.py` isolates each engine; one bad engine → its empty default,
  never a 500.
- **Ethics** — attack-path endpoints are explicitly hypothetical; no action is performed.
- **No new dependencies** — pure stdlib + the frozen contracts.

---

## How to run

```powershell
# either venv — no GPU/ML needed
python -m scripts.phase4_test        # pins graph/risk/attack/fix outputs
python -m scripts.contract_check     # full signals -> intelligence -> Report
```

A live `/analyze` on a rich photo (face + badge text + caption + handle) now returns a
populated exposure graph, non-zero risk meters, an attack path, and fixes.

---

## What's next (Phase 5)

The backend is now **end-to-end complete** (perception → `signals[]` → intelligence →
Report). Phase 5 is the **React + Tailwind + react-flow** frontend that renders the
Report into fixed sections (PLAN §4.1), developed against `GET /sample-report` /
`fixtures/report_sample.json` — no GPU required. Then Phase 6 (deploy / Cloudflare
tunnel) and the optional Phase 7 LLM `explanation`.
