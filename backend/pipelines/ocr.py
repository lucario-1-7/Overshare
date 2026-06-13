"""OCR pipeline (PLAN §4.4) — PHASE 3 LANE.

PaddleOCR primary, EasyOCR fallback. Emits one `screen_text` Signal per detected
text region, each with an `evidence.bbox` so the Annotator can box it, and the
recognized string in BOTH `value` and `evidence.text` so router.py can chain it
into the PII pipeline (PLAN §3 step 4: "OCR output is fed into Presidio").

CONTRACT (do not change the signatures; router.py + loaders.py already call these):
    load_ocr_model(device) -> model | None      # opaque handle (dict wrapper)
    extract_ocr_signals(image_bytes, model) -> List[Signal]

Design rules mirror objects.py / faces.py:
  - heavy imports (paddleocr / easyocr / numpy / PIL) live INSIDE functions
  - never raise — return [] on any error
  - model is None (not loaded / light venv) -> return []
  - inference is serialized (the readers cache per-call state and main.py offloads
    inference to a threadpool, so two concurrent calls could interleave that state)
"""
from __future__ import annotations

import threading
from io import BytesIO
from typing import Any, List, Optional, Tuple

from backend.contracts.signal import Evidence, Signal

# OCR readers are not guaranteed reentrant; main.py runs inference in a threadpool.
_INFER_LOCK = threading.Lock()

# Recognitions below this confidence are too speculative to surface.
_CONF_FLOOR = 0.35
# Cap emitted text signals so a dense screenshot can't flood the report / UI.
_MAX_SIGNALS = 80


def load_ocr_model(device: str = "cpu") -> Optional[Any]:
    """Build PaddleOCR once (EasyOCR fallback). Returns an opaque wrapper
    ``{"kind": "paddleocr"|"easyocr", "reader": obj}`` or None if neither lib is
    installed (light venv) — the caller (router) then skips OCR entirely."""
    use_gpu = device == "cuda"

    # --- Primary: PaddleOCR ---
    try:
        from paddleocr import PaddleOCR

        try:  # newer/older versions differ on accepted kwargs — degrade gracefully
            reader = PaddleOCR(use_angle_cls=True, lang="en", use_gpu=use_gpu, show_log=False)
        except TypeError:
            reader = PaddleOCR(use_angle_cls=True, lang="en")
        print(f"[models] PaddleOCR loaded (use_gpu={use_gpu}).")
        return {"kind": "paddleocr", "reader": reader}
    except Exception as e:  # noqa: BLE001 — ImportError / partial install / init failure
        print(f"[models] PaddleOCR unavailable ({type(e).__name__}: {e}); trying EasyOCR.")

    # --- Fallback: EasyOCR ---
    try:
        import easyocr

        reader = easyocr.Reader(["en"], gpu=use_gpu)
        print(f"[models] EasyOCR loaded (gpu={use_gpu}).")
        return {"kind": "easyocr", "reader": reader}
    except Exception as e:  # noqa: BLE001
        print(f"[models] EasyOCR unavailable ({type(e).__name__}: {e}); skipping OCR.")
        return None


def _clamp01(x: float) -> float:
    x = float(x)
    if x != x:  # NaN -> would fail the pydantic confidence ge/le validator (500); map to 0.
        return 0.0
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def _box_to_xywh(box: Any) -> Optional[List[float]]:
    """A 4-point polygon ([[x,y]*4], both Paddle & EasyOCR) -> [x, y, w, h]."""
    try:
        xs = [float(p[0]) for p in box]
        ys = [float(p[1]) for p in box]
        x, y = min(xs), min(ys)
        w, h = max(xs) - x, max(ys) - y
        if w <= 0 or h <= 0:
            return None
        return [round(x, 1), round(y, 1), round(w, 1), round(h, 1)]
    except Exception:
        return None


def _looks_like_entry(e: Any) -> bool:
    # A Paddle entry is [box, (text, score)] — box is a point list, text is a str.
    return (
        isinstance(e, (list, tuple))
        and len(e) >= 2
        and isinstance(e[0], (list, tuple))
        and isinstance(e[1], (list, tuple))
        and len(e[1]) >= 2
        and isinstance(e[1][0], str)
    )


def _paddle_lines(result: Any) -> List[Tuple[Any, str, float]]:
    """Normalize PaddleOCR's result (wrapped `[page]` or bare `page`) to
    (box, text, score) tuples. Heavily guarded — format varies across versions."""
    out: List[Tuple[Any, str, float]] = []
    if not isinstance(result, (list, tuple)):
        return out
    for item in result:
        if _looks_like_entry(item):
            entries = [item]
        elif isinstance(item, (list, tuple)):
            entries = item
        else:
            continue
        for e in entries or []:
            if not _looks_like_entry(e):
                continue
            try:
                out.append((e[0], str(e[1][0]), float(e[1][1])))
            except Exception:
                continue
    return out


def extract_ocr_signals(image_bytes: bytes, model: Any) -> List[Signal]:
    """Run OCR over the image; emit one `screen_text` Signal per text region."""
    if model is None or not image_bytes:
        return []
    kind = model.get("kind") if isinstance(model, dict) else None
    reader = model.get("reader") if isinstance(model, dict) else None
    if reader is None:
        return []

    try:
        import numpy as np
        from PIL import Image

        rgb = np.array(Image.open(BytesIO(image_bytes)).convert("RGB"))
    except Exception:
        return []  # undecodable image — never raise

    lines: List[Tuple[Any, str, float]] = []
    try:
        with _INFER_LOCK:  # readers cache per-call state — serialize across threads
            if kind == "paddleocr":
                bgr = np.ascontiguousarray(rgb[:, :, ::-1])  # Paddle expects cv2 BGR
                try:
                    result = reader.ocr(bgr, cls=True)
                except TypeError:
                    result = reader.ocr(bgr)
                lines = _paddle_lines(result)
            elif kind == "easyocr":
                for box, text, score in reader.readtext(rgb):
                    lines.append((box, str(text), float(score)))
    except Exception as e:  # noqa: BLE001 — inference / OOM / device error
        print(f"[ocr] inference skipped ({type(e).__name__}: {e}).")
        return []

    source = "paddleocr" if kind == "paddleocr" else "easyocr"
    signals: List[Signal] = []
    for box, text, score in lines:
        try:
            text = (text or "").strip()
            if not text or score < _CONF_FLOOR:
                continue
            bbox = _box_to_xywh(box)
            if bbox is None:
                continue
            signals.append(
                Signal(
                    type="screen_text",
                    value=text,                       # router chains s.value into Presidio
                    source=source,                    # type: ignore[arg-type]
                    confidence=_clamp01(score),
                    evidence=Evidence(bbox=bbox, text=text, raw={"score": round(float(score), 3)}),
                )
            )
        except Exception:
            continue
        if len(signals) >= _MAX_SIGNALS:
            break
    return signals
