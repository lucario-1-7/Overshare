"""Phase 3 model-loading seam — PHASE 3 LANE.  [STUB — fill this in]

main.py's lifespan calls this ONCE at startup (after YOLO/RetinaFace) so the Phase 3
person never has to edit main.py. Stash your loaded handles into the shared MODELS
dict under the exact keys router.py reads:

    models["ocr"]  -> the OCR reader        (read by router via models.get("ocr"))
    models["pii"]  -> the Presidio engine   (read by router via models.get("pii"))

`device` is "cuda" or "cpu" (already decided by main.py). Failures must be non-fatal:
if a model can't load, leave its key as None and the pipeline degrades to skipping it
(reliability first — the server still boots and serves whatever did load).
"""
from __future__ import annotations

from backend.pipelines.ocr import load_ocr_model
from backend.pipelines.pii import load_pii_engine


def load_phase3_models(models: dict, device: str = "cpu") -> None:
    """PHASE 3: populate models["ocr"] and models["pii"]. Currently no-ops (return None)
    so the server boots EXIF+YOLO+RetinaFace only until Phase 3 lands."""
    models["ocr"] = load_ocr_model(device)
    models["pii"] = load_pii_engine()
