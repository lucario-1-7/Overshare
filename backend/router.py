"""Input dispatch (PLAN §3 step 3, §4.3).

Classifies the request payload and fires the relevant pipelines, each of which
appends Signals to one shared list. A single request may carry several inputs
(photo *and* caption *and* handle) -> all relevant pipelines run.

Phase 1: only the image -> EXIF path is live. The text and username branches are
stubbed so the contract is already correct; Phase 3/4 fill them in.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from backend.contracts.signal import Signal
from backend.pipelines.exif import extract_exif_signals


def run_pipelines(
    image_bytes: Optional[bytes] = None,
    text: Optional[str] = None,
    username: Optional[str] = None,
) -> Tuple[List[Signal], List[str]]:
    """Returns (signals, models_run)."""
    signals: List[Signal] = []
    models_run: List[str] = []

    if image_bytes:
        signals.extend(extract_exif_signals(image_bytes))
        models_run.append("exif")
        # Phase 2+: YOLO (objects/home), RetinaFace (faces), PaddleOCR -> Presidio.

    if text:
        # Phase 3: Presidio + spaCy over caption text.
        pass

    if username:
        # Phase 4: footprint existence checks via requests.
        pass

    return signals, models_run
