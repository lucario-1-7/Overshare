"""PII pipeline (PLAN §4.4) — PHASE 3 LANE.  [STUB — fill this in]

Presidio + spaCy over free text. The SAME function runs over two text sources:
  1) the caption/text input (router passes it directly), and
  2) the OCR'd `screen_text` from ocr.py (router chains it in — PLAN §3 step 4).

CONTRACT (do not change the signature; router.py already calls it):
    load_pii_engine() -> engine | None
    extract_pii_signals(text, engine) -> List[Signal]

Each emitted Signal MUST be:
    type     = one of "person_name" | "employer" | "email" | "phone"
               | "location" | "address"   (map Presidio entities to these)
    source   = "presidio"
    value    = the detected span (e.g. "ACME Corp", "john@acme.com")
    confidence = Presidio score in [0, 1]
    evidence = Evidence(text=<the surrounding span>)   # no bbox (text has no box)

Suggested Presidio->type mapping:
    PERSON->person_name, ORG->employer, EMAIL_ADDRESS->email,
    PHONE_NUMBER->phone, LOCATION->location, (address-like)->address

Rules: heavy imports inside functions; never raise (return []); engine None -> [].
"""
from __future__ import annotations

from typing import Any, List, Optional

from backend.contracts.signal import Signal  # noqa: F401  (used once implemented)


def load_pii_engine() -> Optional[Any]:
    """PHASE 3: build the Presidio AnalyzerEngine (spaCy en_core_web_lg) once.
    Return None if not installed. See requirements-ml.txt."""
    # TODO(phase3): construct and return the Presidio analyzer; import inside.
    return None


def extract_pii_signals(text: str, engine: Any) -> List[Signal]:
    """PHASE 3: run Presidio over `text`; emit person_name/employer/email/phone/
    location/address Signals. Return [] if engine is None, text is empty, or on error."""
    if engine is None or not text or not text.strip():
        return []
    # TODO(phase3): analyzer.analyze(text=text, language="en"); map results -> Signals.
    return []
