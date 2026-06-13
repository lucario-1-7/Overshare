"""RetinaFace face-DETECTION pipeline (PLAN §4.4) — torch backend via facexlib.

Emits one `face` Signal per detected face, each with an `evidence.bbox` so the
Annotator draws a box around it. The signal `value` records the count ("face 1 of 3").

**Ethics/scope guard (PLAN §4.4):** this DETECTS faces only. It never recognizes,
matches, or identifies anyone. "Face matched against the web" exists only as a
hypothetical step in the attack narrative (Phase 4), never as something we perform.

Backend note: we use facexlib's pure-PyTorch RetinaFace (resnet50) rather than the
TensorFlow `retina-face` package, so the whole perception stack is one framework on
the GPU (TensorFlow has no native-Windows GPU support). The emitted contract — a
`face` signal with `source="retinaface"` and a bbox — is identical either way.

Design rules mirror objects.py / exif.py: lazy heavy imports, never raises, model
is injected once at startup (None → skip).
"""
from __future__ import annotations

import threading
from io import BytesIO
from typing import Any, List, Optional

from backend.contracts.signal import Evidence, Signal

# Faces below this detector score are too uncertain to surface.
_CONF_FLOOR = 0.80
# Cap emitted face signals (a crowd photo shouldn't flood the report / annotation).
_MAX_FACES = 50

# facexlib's RetinaFace is NOT reentrant: detect_faces() writes per-image scale
# factors (self.scale / self.resize) onto the shared model instance and reads them
# back to rescale boxes. Since main.py offloads inference to a threadpool (up to ~40
# worker threads share this one loaded model), two concurrent differently-sized
# images would interleave those writes -> silently mislocated boxes. Serialize the
# forward pass with a lock. Throughput cost is ~nil: GPU work is already serialized
# on the default CUDA stream anyway.
_INFER_LOCK = threading.Lock()


def load_face_model(device: str = "cpu") -> Optional[Any]:
    """Load the RetinaFace detector once at startup. Returns the net, or None if
    facexlib/torch isn't installed (light venv) or weights can't be fetched."""
    try:
        from facexlib.detection import init_detection_model
    except Exception as e:  # noqa: BLE001 — ImportError / partial install
        print(f"[models] RetinaFace unavailable ({type(e).__name__}: {e}); skipping faces.")
        return None
    try:
        net = init_detection_model("retinaface_resnet50", half=False, device=device)
        net.eval()
        print(f"[models] RetinaFace (resnet50) loaded on {device}.")
        return net
    except Exception as e:  # noqa: BLE001 — weight download / CUDA init failure
        print(f"[models] RetinaFace load failed ({type(e).__name__}: {e}); skipping faces.")
        return None


def _clamp01(x: float) -> float:
    x = float(x)
    if x != x:  # NaN (rare numerical-instability output) -> would fail the pydantic
        return 0.0  # confidence ge/le validator and 500 the request; map to 0.
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def extract_face_signals(image_bytes: bytes, model: Any) -> List[Signal]:
    """Detect faces and emit one `face` Signal per face, each with a bbox."""
    if model is None or not image_bytes:
        return []
    try:
        import numpy as np
        import torch
        from PIL import Image
    except Exception:
        return []

    try:
        rgb = np.array(Image.open(BytesIO(image_bytes)).convert("RGB"))
        # facexlib's RetinaFace subtracts a BGR mean, so feed it BGR (cv2 convention).
        # ascontiguousarray avoids the negative-stride view that torch.from_numpy rejects.
        bgr = np.ascontiguousarray(rgb[:, :, ::-1])
    except Exception:
        return []

    try:
        with _INFER_LOCK:  # the model instance is shared across threads — serialize it
            with torch.no_grad():
                dets = model.detect_faces(bgr, conf_threshold=_CONF_FLOOR)
    except Exception as e:  # noqa: BLE001 — inference / OOM / device error
        print(f"[faces] RetinaFace inference skipped ({type(e).__name__}: {e}).")
        return []

    # detect_faces returns an ndarray/list of rows: [x1, y1, x2, y2, score, *landmarks]
    rows = list(dets) if dets is not None else []
    n = min(len(rows), _MAX_FACES)
    signals: List[Signal] = []
    for i in range(n):
        # Whole per-face body is guarded: any unexpected value (e.g. a NaN that
        # slipped a clamp) drops that one face rather than 500-ing the request.
        try:
            row = rows[i]
            x1, y1, x2, y2, score = (float(row[j]) for j in range(5))
            w, h = x2 - x1, y2 - y1
            if w <= 0 or h <= 0:
                continue
            signals.append(
                Signal(
                    type="face",
                    value=f"face {i + 1} of {n}",
                    source="retinaface",
                    confidence=_clamp01(score),
                    evidence=Evidence(
                        bbox=[round(x1, 1), round(y1, 1), round(w, 1), round(h, 1)],
                        raw={"score": round(score, 3), "index": i + 1, "total": n},
                    ),
                )
            )
        except Exception:
            continue
    return signals
