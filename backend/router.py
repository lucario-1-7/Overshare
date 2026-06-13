"""Input dispatch (PLAN §3 step 3, §4.3).

Classifies the request payload and fires the relevant pipelines, each of which
appends Signals to one shared list. A single request may carry several inputs
(photo *and* caption *and* handle) -> all relevant pipelines run.

Phase 2: the image path runs EXIF (always) + YOLOv8 objects + RetinaFace faces.
The perception models are passed in from the app's loaded-once registry (PLAN §4.2);
when a model is None (light venv / failed load) its pipeline simply contributes
nothing — the request still succeeds with whatever else ran ("reliability first").
The text and username branches stay stubbed for Phase 3/4.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from backend.contracts.signal import Signal
from backend.pipelines.exif import extract_exif_signals
from backend.pipelines.faces import extract_face_signals
from backend.pipelines.footprint import extract_footprint_signals
from backend.pipelines.objects import extract_object_signals
from backend.pipelines.ocr import extract_ocr_signals
from backend.pipelines.pii import extract_pii_signals


def run_pipelines(
    image_bytes: Optional[bytes] = None,
    text: Optional[str] = None,
    username: Optional[str] = None,
    models: Optional[dict] = None,
) -> Tuple[List[Signal], List[str]]:
    """Returns (signals, models_run). `models` is the app's loaded-once registry."""
    models = models or {}
    device = models.get("device", "cpu")
    signals: List[Signal] = []
    models_run: List[str] = []

    if image_bytes:
        # EXIF is pure-Python and always runs.
        signals.extend(extract_exif_signals(image_bytes))
        models_run.append("exif")

        # YOLOv8 objects (home indicators / person / document) — only if loaded.
        yolo = models.get("yolo")
        if yolo is not None:
            signals.extend(extract_object_signals(image_bytes, yolo, device))
            models_run.append("yolo")

        # RetinaFace face detection — only if loaded.
        face = models.get("face")
        if face is not None:
            signals.extend(extract_face_signals(image_bytes, face))
            models_run.append("retinaface")

        # PaddleOCR (Phase 3) -> screen_text, whose text is then chained into Presidio
        # (PLAN §3 step 4: "OCR output is fed into Presidio").
        ocr = models.get("ocr")
        if ocr is not None:
            ocr_signals = extract_ocr_signals(image_bytes, ocr)
            signals.extend(ocr_signals)
            models_run.append("paddleocr")
            ocr_text = " ".join(
                s.value for s in ocr_signals if s.type == "screen_text" and s.value
            )
            pii_engine = models.get("pii")
            if pii_engine is not None and ocr_text.strip():
                signals.extend(extract_pii_signals(ocr_text, pii_engine))
                if "presidio" not in models_run:
                    models_run.append("presidio")

    # Caption / free text -> Presidio (Phase 3), same engine as the OCR chain.
    if text:
        pii_engine = models.get("pii")
        if pii_engine is not None:
            signals.extend(extract_pii_signals(text, pii_engine))
            if "presidio" not in models_run:
                models_run.append("presidio")

    # Username / email -> footprint existence checks (Phase 3, no model).
    if username:
        signals.extend(extract_footprint_signals(username))
        models_run.append("footprint")

    return signals, models_run
