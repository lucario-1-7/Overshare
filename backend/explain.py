"""Optional LLM explanation (PLAN §4.11) — PHASE 7.

The ONLY generative-AI layer in Overshare. Reads the assembled Report and writes one
plain-English paragraph summarising the exposure for the user.

Connection rule (PLAN §4.11, §10 cut-line #1): purely additive and **non-blocking** —
wrapped in try/except with a timeout. If Ollama is down, slow, or not installed, this
returns None *fast* and the report ships without an `explanation`. It is NEVER on the
critical path.

Local Ollama only — no external model API in the critical path (PLAN §7), so the
"nothing leaves this machine" guarantee holds. Configurable via env:
    OLLAMA_HOST     (default http://localhost:11434)
    OLLAMA_MODEL    (default llama3.2)
    OLLAMA_TIMEOUT  (seconds, default 20)
    OVERSHARE_NO_LLM=1  -> skip entirely
"""
from __future__ import annotations

import os
from typing import Optional

from backend.contracts.report import Report


def _prompt(report: Report) -> str:
    """A compact, grounded prompt built only from what was actually detected."""
    seen: set = set()
    facts = []
    for s in report.signals:
        if s.type in seen:
            continue
        seen.add(s.type)
        facts.append(f"- {s.type}: {s.value}")
    facts_block = "\n".join(facts) or "- (nothing detected)"
    r = report.risks
    attack = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(report.attackPath))

    return (
        "You are a privacy analyst. Based ONLY on the detected items below from a single "
        'image or post the user is about to share, write ONE short paragraph (3-4 sentences) '
        'in plain English, addressed to the user as "you", explaining what a stranger could '
        "learn and why it is risky. Do not use markdown, bullet points, or a preamble, and do "
        "not invent any detail that is not listed.\n\n"
        f"Detected:\n{facts_block}\n\n"
        f"Risk scores (0-100): doxxing {r.doxxing}, stalking {r.stalking}, phishing {r.phishing}.\n\n"
        f"How an attacker could chain it:\n{attack or '(no clear chain)'}\n\n"
        "Write the paragraph now:"
    )


def generate_explanation(report: Report) -> Optional[str]:
    """Ask a local Ollama model for the explanation paragraph. Returns None on any
    failure (Ollama down/slow/absent, bad response) — the report ships regardless."""
    if os.environ.get("OVERSHARE_NO_LLM") == "1":
        return None
    if not report.signals:
        return None  # honest when clean — nothing to explain

    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    model = os.environ.get("OLLAMA_MODEL", "llama3.2")
    try:
        timeout = float(os.environ.get("OLLAMA_TIMEOUT", "20"))
    except ValueError:
        timeout = 20.0

    try:
        import requests
    except Exception:
        return None  # requests not installed (light venv) -> skip

    try:
        resp = requests.post(
            f"{host.rstrip('/')}/api/generate",
            json={
                "model": model,
                "prompt": _prompt(report),
                "stream": False,
                "options": {"temperature": 0.4, "num_predict": 220},
            },
            timeout=timeout,
        )
        if resp.status_code != 200:
            return None
        text = (resp.json().get("response") or "").strip()
        return text or None
    except Exception:
        return None  # connection refused / timeout / bad JSON -> non-blocking skip
