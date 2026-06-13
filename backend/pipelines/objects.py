"""YOLOv8 object pipeline (PLAN §4.4) — stock COCO weights, local GPU.

Emits privacy-relevant object Signals, each carrying an `evidence.bbox` so the
Annotator (PLAN §4.6) can draw a labelled box on the image:

  - `person`         : a person is visible in the shot
  - `home_indicator` : domestic context (bed/sofa/tv/laptop/...) → "this was taken
                       somewhere private", which fuses with GPS into a home-locatable risk
  - `document`       : a book/paper-like object that may carry readable PII (COCO's
                       closest class is "book"; OCR in Phase 3 reads what's on it)

Design rules (match the EXIF pipeline):
  - **Heavy imports are lazy.** Nothing here imports torch/ultralytics/numpy at module
    load, so the light Phase-1 venv can still import the backend and run EXIF-only.
  - **Never raises.** A bad image or a model hiccup yields zero signals, never a 500.
  - **Model is injected.** `model is None` (not loaded / not installed) → no signals.
    The single load happens once at app startup (PLAN §4.2), never per-request.
"""
from __future__ import annotations

import threading
from io import BytesIO
from typing import Any, List, Optional

from backend.contracts.signal import Evidence, Signal

# ultralytics caches a single predictor on the model and stores per-call state
# (batch/results/dataset) on it; concurrent predict() calls from the threadpool
# (main.py offloads inference) would interleave that state -> wrong/mismatched
# detections. Serialize the forward pass. (GPU work serializes on the default CUDA
# stream regardless, so the throughput cost is negligible.)
_INFER_LOCK = threading.Lock()

# COCO class name -> the Signal `type` we report it as. Only privacy-relevant
# classes are mapped; everything else YOLO sees (car, bottle, ...) is ignored so
# the signal list stays meaningful. `value` carries the concrete COCO label.
_COCO_TO_TYPE = {
    "person": "person",
    "book": "document",  # COCO's nearest "document" proxy; OCR (Phase 3) reads it
    # Domestic / personal-space indicators (PLAN §4.4 "bed/sofa/tv"):
    "bed": "home_indicator",
    "couch": "home_indicator",
    "chair": "home_indicator",
    "dining table": "home_indicator",
    "toilet": "home_indicator",
    "tv": "home_indicator",
    "laptop": "home_indicator",
    "cell phone": "home_indicator",
    "refrigerator": "home_indicator",
    "oven": "home_indicator",
    "microwave": "home_indicator",
    "sink": "home_indicator",
    "potted plant": "home_indicator",
}

# Detection confidence floor — below this YOLO boxes are too speculative to show.
_CONF_FLOOR = 0.35
# Hard cap on emitted object signals so a busy scene can't flood the report / UI.
_MAX_SIGNALS = 40


def load_yolo_model(device: str = "cpu") -> Optional[Any]:
    """Load YOLOv8-nano once at startup. Returns the model, or None if ultralytics
    isn't installed (light venv) or weights can't be fetched — caller degrades."""
    try:
        from ultralytics import YOLO
    except Exception as e:  # noqa: BLE001 — ImportError or partial install
        print(f"[models] YOLO unavailable ({type(e).__name__}: {e}); skipping objects.")
        return None
    try:
        model = YOLO("yolov8n.pt")  # auto-downloads to the ultralytics cache on first run
        # Warm + pin to the device so the first real request isn't slow / on the wrong device.
        actual = device
        try:
            model.to(device)
        except Exception as e:  # noqa: BLE001 — don't hide a failed device pin
            actual = "cpu(?)"
            print(f"[models] YOLO .to({device}) failed ({type(e).__name__}: {e}); "
                  f"model stays on its default device.")
        print(f"[models] YOLOv8n loaded (requested {device}, on {actual}).")
        return model
    except Exception as e:  # noqa: BLE001 — weight download / CUDA init failure
        print(f"[models] YOLO load failed ({type(e).__name__}: {e}); skipping objects.")
        return None


def _clamp01(x: float) -> float:
    x = float(x)
    if x != x:  # NaN -> would fail the pydantic confidence ge/le validator (500); map to 0.
        return 0.0
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def extract_object_signals(
    image_bytes: bytes, model: Any, device: str = "cpu"
) -> List[Signal]:
    """Run YOLOv8 over the image and map detections to Signals with bboxes."""
    if model is None or not image_bytes:
        return []
    try:
        from PIL import Image

        img = Image.open(BytesIO(image_bytes)).convert("RGB")
    except Exception:
        return []  # undecodable image — honest-when-broken, never raise

    try:
        with _INFER_LOCK:  # the model/predictor is shared across threads — serialize it
            results = model.predict(img, conf=_CONF_FLOOR, device=device, verbose=False)
    except Exception as e:  # noqa: BLE001 — inference / OOM / device error
        print(f"[objects] YOLO inference skipped ({type(e).__name__}: {e}).")
        return []

    signals: List[Signal] = []
    names = getattr(model, "names", {}) or {}
    for res in results:
        boxes = getattr(res, "boxes", None)
        if boxes is None:
            continue
        for box in boxes:
            # Whole per-box body guarded: a malformed box / clamp edge case drops that
            # one detection rather than 500-ing the request (the "never raises" rule).
            try:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                # xyxy -> [x, y, w, h] (the frozen Evidence.bbox convention)
                x1, y1, x2, y2 = (float(v) for v in box.xyxy[0])
                label = str(names.get(cls_id, cls_id))
                sig_type = _COCO_TO_TYPE.get(label)
                if sig_type is None:
                    continue  # not privacy-relevant — ignore
                w, h = x2 - x1, y2 - y1
                if w <= 0 or h <= 0:
                    continue
                signals.append(
                    Signal(
                        type=sig_type,
                        value=label,
                        source="yolo",
                        confidence=_clamp01(conf),
                        evidence=Evidence(
                            bbox=[round(x1, 1), round(y1, 1), round(w, 1), round(h, 1)],
                            text=label,
                            raw={"coco": label, "conf": round(conf, 3)},
                        ),
                    )
                )
            except Exception:
                continue
            if len(signals) >= _MAX_SIGNALS:
                return signals
    return signals
