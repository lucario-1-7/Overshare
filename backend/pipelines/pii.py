"""PII pipeline (PLAN §4.4) — PHASE 3 LANE.

Presidio + spaCy over free text. The SAME function runs over two text sources
(router.py wires both): the caption/text input, and the OCR'd `screen_text`.

CONTRACT (do not change the signatures; router.py + loaders.py already call these):
    load_pii_engine() -> engine | None
    extract_pii_signals(text, engine) -> List[Signal]

Presidio entity -> our Signal `type`:
    PERSON->person_name, ORGANIZATION/ORG->employer, EMAIL_ADDRESS->email,
    PHONE_NUMBER->phone, LOCATION->location, *ADDRESS*->address.

Design rules mirror the other pipelines: heavy imports inside functions; never
raise (return []); engine None / empty text -> [].
"""
from __future__ import annotations

from typing import Any, List, Optional

from backend.contracts.signal import Evidence, Signal

# Presidio entity_type -> frozen SignalType. Anything not here is ignored so the
# signal list stays meaningful for the downstream intelligence layer.
_ENTITY_TO_TYPE = {
    "PERSON": "person_name",
    "ORGANIZATION": "employer",
    "ORG": "employer",
    "EMAIL_ADDRESS": "email",
    "PHONE_NUMBER": "phone",
    "LOCATION": "location",
    "GPE": "location",
    "NRP": "location",
}

# Only the entities we actually map — passed to Presidio so it doesn't waste work.
_WANTED_ENTITIES = sorted(set(_ENTITY_TO_TYPE) | {"US_DRIVER_LICENSE"})  # harmless extras ignored
_SCORE_FLOOR = 0.35
_MAX_SIGNALS = 60


def load_pii_engine() -> Optional[Any]:
    """Build the Presidio AnalyzerEngine (spaCy en_core_web_lg) once. Returns None
    if Presidio/spaCy/the model aren't installed (light venv) — caller skips PII."""
    try:
        from presidio_analyzer import AnalyzerEngine
        from presidio_analyzer.nlp_engine import NlpEngineProvider
    except Exception as e:  # noqa: BLE001 — ImportError / partial install
        print(f"[models] Presidio unavailable ({type(e).__name__}: {e}); skipping PII.")
        return None
    try:
        provider = NlpEngineProvider(
            nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}],
            }
        )
        nlp_engine = provider.create_engine()  # raises if en_core_web_lg isn't downloaded
        engine = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])
        print("[models] Presidio analyzer loaded (spaCy en_core_web_lg).")
        return engine
    except Exception as e:  # noqa: BLE001 — missing spaCy model / init failure
        print(f"[models] Presidio load failed ({type(e).__name__}: {e}); skipping PII. "
              f"Did you run `python -m spacy download en_core_web_lg`?")
        return None


def _clamp01(x: float) -> float:
    x = float(x)
    if x != x:  # NaN -> pydantic confidence validator would 500; map to 0.
        return 0.0
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def _map_type(entity_type: str) -> Optional[str]:
    t = _ENTITY_TO_TYPE.get(entity_type)
    if t is not None:
        return t
    if "ADDRESS" in (entity_type or ""):  # STREET_ADDRESS / *ADDRESS* -> address
        return "address"
    return None


def extract_pii_signals(text: str, engine: Any) -> List[Signal]:
    """Run Presidio over `text`; emit person_name/employer/email/phone/location/
    address Signals. Returns [] if engine is None, text is empty, or on any error."""
    if engine is None or not text or not text.strip():
        return []
    try:
        results = engine.analyze(text=text, language="en", entities=_WANTED_ENTITIES)
    except Exception:
        try:  # some versions reject an explicit `entities` filter — analyze all.
            results = engine.analyze(text=text, language="en")
        except Exception as e:  # noqa: BLE001
            print(f"[pii] analyze skipped ({type(e).__name__}: {e}).")
            return []

    signals: List[Signal] = []
    seen: set = set()  # de-dupe identical (type, value) spans across the two text sources
    for r in results or []:
        try:
            sig_type = _map_type(getattr(r, "entity_type", ""))
            if sig_type is None:
                continue
            score = float(getattr(r, "score", 0.0))
            if score < _SCORE_FLOOR:
                continue
            span = text[r.start:r.end].strip()
            if len(span) < 2:
                continue
            key = (sig_type, span.lower())
            if key in seen:
                continue
            seen.add(key)
            signals.append(
                Signal(
                    type=sig_type,                    # type: ignore[arg-type]
                    value=span,
                    source="presidio",
                    confidence=_clamp01(score),
                    evidence=Evidence(text=span, raw={"entity": getattr(r, "entity_type", "")}),
                )
            )
        except Exception:
            continue
        if len(signals) >= _MAX_SIGNALS:
            break
    return signals
