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
from backend.pipelines.objects import extract_object_signals


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

        # Phase 3+: PaddleOCR -> Presidio over the same image.

    if text:
        # Phase 3: Presidio + spaCy over caption text.
        pass

    if username:
        # Phase 4: footprint existence checks via requests.
        pass

    return signals, models_run
