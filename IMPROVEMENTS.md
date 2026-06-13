# Overshare — Improvements Backlog (perceived-value phase)

> **Framing:** the build is feature-complete enough to demo (Perception ✅ Inference ✅
> Graph ✅ Risk ✅ Attack Path ✅ Frontend ✅ LLM ✅). We are **no longer in "build more
> features"** — we're in **"increase perceived value."** The next jump in score comes
> from **storytelling, metrics, demo flow, and visualization**, not more models.
> Rule of thumb for the time left: **~1 hour coding, ~5 hours making the demo
> impossible to forget.**

---

## Highest-ROI improvements

### 1. Attack **Timeline** (not just a list) — *P1*
Turn the attack path into a time-stamped simulation; worth more presentation points
than another model. *(Lives in: `backend/intelligence/attack.py` output + Phase 5 UI.)*

```
ATTACK SIMULATION
  T+0 sec   Face visible
  T+30 sec  Employer identified
  T+2 min   Identity correlated
  T+5 min   Targeted phishing feasible
```

### 2. Privacy **Recovery Score** (before → after fixes) — *P1*
The biggest missing product metric. Completes the story: Problem → Detection → Fix →
**measurable Improvement.** *(Lives in: re-score after fixes — Risk Engine re-run on the
post-fix signal set; surface in Phase 5 UI.)*

```
Exposure Score: 84  →  31      Risk Reduction: 63%
```

### 3. **Attacker Effort** badge — *P1*
Cheap and memorable. Derive a LOW/MED/HIGH + estimated time from the present signal
set. *(Lives in: a small rule over signal types; add to Report/UI.)*

```
Attacker Effort: LOW   ·   Est. time: < 5 minutes
Derived from: Face + Employer + Username
```

### 4. **Inference Amplification** — *P1*
Quantifies our actual innovation (signals → derived inferences). *(Lives in: count raw
signals vs derived graph inferences/attack steps; add to Report/UI.)*

```
Raw signals found: 4   ·   Derived inferences: 11   ·   Amplification: 2.75×
```

---

## Graph: make the **fusion nodes the stars** — *P1*
The fusion nodes (`home_locatable`, `identity_linkable`) are where the IP lives — make
them **visually distinct** (color/size/glow) in react-flow. *(Lives in: Phase 5 `web/`.)*

```
Face ─┐
      ├─► Identity Exposure   ← visually highlighted fusion node
Employer ─┘
```

---

## Demo = the biggest remaining risk (not technical)
Curate a **fixed demo dataset** so a live run can never flop:
- **Demo Image #1 — guaranteed rich result:** contains Face + Badge + Laptop + GPS →
  always produces a full graph + high scores + attack path.
- **Demo Image #2 — clean image:** produces *"nothing significant found"* → shows
  **honesty** (judges appreciate the "honest when clean" path). *P1*

---

## Do **NOT** build (no meaningful score gain now)
GeoCLIP · license-plate model · more OCR · more CV models · more LLM agents · RAG ·
vector DB. Adding any of these trades demo-polish time for ~nothing.

---

## Priority order
- **P0 — Cloudflare Tunnel** (without it, Shippedness is hurt) ← do first.
- **P1 — Attack Timeline · Privacy Recovery Score · Demo Dataset · fusion-node styling · Attacker Effort · Inference Amplification.**
- **P2 — Deck · Demo Script.**
- **P3 — LLM polish** (only after everything above).

---

## Judge score estimate (assuming deployment works)
| Category | Estimate |
|---|---|
| Craft | 8.5–9 / 10 |
| Product Thinking | 9–9.5 / 10 |
| AI Integration | 8.5–9.5 / 10 |
| Design | depends on frontend |
| Shippedness | depends on the tunnel |
| Presentation | depends on the demo |

**Bottom line:** the remaining gains are in storytelling, metrics, demo flow, and
visualization — not engineering.
