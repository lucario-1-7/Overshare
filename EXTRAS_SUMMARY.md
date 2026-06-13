# Overshare — Extra Features: Digital-Footprint Module

> **Goal:** extend Overshare from an image/text privacy scanner into a **digital-footprint
> intelligence** product by adding real **online-identity** signals — without touching the
> core. Built as an **isolated, opt-in `backend/extras/` package** with its own endpoint,
> so `/analyze` and the frozen Signal/Report contracts keep working **byte-identically**.

**Status: complete, live-verified, additive, on `main`.** ✅

---

## Why it's "extra" (and safe)
- Lives entirely in **`backend/extras/`** with its **own models** — so it adds new signal
  kinds (`breach_exposure`, `platform_presence`, `email_domain`, `gravatar_profile`,
  `organization`) **without editing `backend/contracts/`**.
- The **only** core touch is a single **guarded `include_router`** line in `main.py`,
  wrapped so a broken/absent extras package can never take down the core API.
- All external calls are **free + key-free**, bounded by short timeouts, **never raise**,
  and have a **canned fallback** so a live demo can't hang.

---

## What was built

### 1. Collectors — `backend/extras/collectors.py` (free, no key)
| Source | What it returns | Signal |
|---|---|---|
| **XposedOrNot** | breach count + names for an email | `breach_exposure` |
| **Curated presence** (GitHub / Reddit / GitLab / dev.to) | which public accounts exist (clean 200/404) | `platform_presence` |
| **Email domain** (no network) | personal vs corporate (+ inferred org) | `email_domain`, `organization` |
| **Gravatar** | does the email have a public profile/avatar | `gravatar_profile` |

> LinkedIn / Instagram / X are intentionally **excluded** — they're login-walled and would
> false-positive. We only report sources we can verify honestly.

### 2. Footprint engine — `backend/extras/footprint.py` (deterministic)
Turns the collected signals into the product layer:
- **Digital Footprint Score** (0–100) from four categories — Personal identity,
  Professional identity, Contactability, Cross-platform presence.
- **Attacker Effort** (LOW/MED/HIGH + ETA — low effort = high exposure).
- **Inference Amplification** (raw inputs → derived inferences, e.g. `2 → 6 = 3.0×`).
- **Time-to-Exploit timeline** (T+0s … T+15m).

### 3. API — `backend/extras/api.py`
- `POST /extras/footprint` `{ "email": "...", "username": "..." }` → a `FootprintReport`.
- `GET /extras/health`. Collectors run in a threadpool (never block the event loop).

### 4. `scripts/extras_test.py` — acceptance test (live + deterministic).

---

## Verification

`python -m scripts.extras_test` — **all assertions pass:**

| Check | Result |
|---|---|
| Email domain | gmail → personal · acme.com → corporate (+ org) |
| Footprint scoring | score=78, effort=LOW, amplification=3.0×, 6 timeline steps; deterministic |
| Canned collect | demo persona → breach + 4 platforms + domain, no network |
| `/extras/footprint` endpoint | 200 + valid `FootprintReport` |
| **Core unchanged** | `/health`, `/sample-report`, `/analyze` all still 200 |

**Genuinely real (not faked):** a live XposedOrNot lookup returned **197 real breaches**
for a test email; `torvalds` resolved to real GitHub + GitLab. Core regression
(`contract_check`, `smoke_test`, `phase4_test`, `phase7_test`) all remain green.

---

## How to use
```bash
# core (unchanged):      POST /analyze            (image / text / username)
# extra footprint:       POST /extras/footprint   {"email": "...", "username": "..."}
#                        GET  /extras/health
OVERSHARE_CANNED=1       # optional: deterministic demo persona, zero network (demo-safe)
```

---

## Privacy framing
Image analysis stays **local**; footprint lookups send **only the identifier you enter**
(email/username) — never an image — and the report's `meta.sentToExternal` shows exactly
what left the machine.

---

## What's next
Wire the footprint panel into the **frontend (`web/`)** as an "Additional: Digital
Footprint" section, then **Phase 6 — public Cloudflare tunnel** (Shippedness) and the
**demo dataset + deck**.
