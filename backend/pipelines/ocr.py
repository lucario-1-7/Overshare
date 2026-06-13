"""OCR pipeline (PLAN §4.4) — PHASE 3 LANE.  [STUB — fill this in]

CONTRACT (do not change the signature; router.py already calls it):
    load_ocr_model(device) -> model | None      # PaddleOCR (EasyOCR fallback)
    extract_ocr_signals(image_bytes, model) -> List[Signal]

Each emitted Signal MUST be:
    type     = "screen_text"
    source   = "paddleocr"  (or "easyocr" if you use the fallback)
    value    = the recognized text string
    confidence = OCR confidence in [0, 1]
    evidence = Evidence(bbox=[x, y, w, h], text=<recognized string>)
               bbox drives the Annotator box (already built, do not touch).

Why screen_text matters: router.py chains your recognized text into the PII
pipeline (pii.py) — PLAN §3 step 4 "OCR output is fed into Presidio". Put the
readable string in BOTH `value` and `evidence.text` so the chain can read it.

Rules to match the existing pipelines (exif/objects/faces):
  - heavy imports (paddleocr/torch/numpy/cv2) go INSIDE functions, never at module top
  - never raise — return [] on any error
  - model is None (not loaded / light venv) -> return []
"""
from __future__ import annotations

from typing import Any, List, Optional

from backend.contracts.signal import Signal  # noqa: F401  (used once implemented)


def load_ocr_model(device: str = "cpu") -> Optional[Any]:
    """PHASE 3: build PaddleOCR once (e.g. PaddleOCR(use_angle_cls=True, lang='en')).
    Return the reader, or None if the lib isn't installed. See requirements-ml.txt."""
    # TODO(phase3): load PaddleOCR (EasyOCR fallback); import inside this function.
    return None


def extract_ocr_signals(image_bytes: bytes, model: Any) -> List[Signal]:
    """PHASE 3: run OCR over the image; emit one `screen_text` Signal per text region
    with its bbox. Return [] if model is None or on any error."""
    if model is None or not image_bytes:
        return []
    # TODO(phase3): decode image, run model.ocr(...), build screen_text Signals.
    return []
