"""The Signal contract — the universal currency of the app (PLAN §1).

Every extractor (EXIF, faces, OCR, objects, PII, footprint) emits zero or more
Signal objects onto one shared list. Nothing downstream cares *which* model
produced a signal — only its `type`. FREEZE THIS SCHEMA.
"""
from __future__ import annotations

from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


def _json_safe(v: Any) -> Any:
    """Coerce arbitrary values into JSON-serializable primitives.

    `evidence.raw` is `Any` by contract ("anything for debugging"), so Phase 2+
    extractors may drop library objects in (Pillow IFDRational, numpy scalars,
    bytes, tensors...). This keeps the FROZEN contract serializable no matter
    what, so the /analyze response can never 500 at the serialization seam.
    """
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, dict):
        return {str(k): _json_safe(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [_json_safe(x) for x in v]
    try:
        return float(v)  # IFDRational, numpy scalars, Decimal, ...
    except (TypeError, ValueError):
        return str(v)    # bytes, tensors, anything else -> debuggable string

# Canonical signal types (PLAN §1) plus the extras named in §4.4
# (`person` from YOLO, `address` from Presidio).
SignalType = Literal[
    "gps",
    "face",
    "employer",
    "location",
    "person_name",
    "email",
    "phone",
    "username",
    "home_indicator",
    "device",
    "timestamp",
    "screen_text",
    "document",
    "person",
    "address",
]

# Which extractor produced the signal (PLAN §1 `source` + §4.4 fallbacks).
SignalSource = Literal[
    "exif",
    "retinaface",
    "paddleocr",
    "easyocr",
    "yolo",
    "presidio",
    "footprint",
]


class Evidence(BaseModel):
    """Optional supporting detail — used for annotation and the UI."""

    bbox: Optional[List[float]] = None  # [x, y, w, h] — drives bounding boxes
    text: Optional[str] = None          # raw OCR/NER span
    raw: Optional[Any] = None           # anything for debugging (coerced JSON-safe)

    @field_validator("raw")
    @classmethod
    def _coerce_raw(cls, v: Any) -> Any:
        return _json_safe(v)


class Signal(BaseModel):
    type: SignalType
    value: str                          # extracted value or label
    source: SignalSource
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: Optional[Evidence] = None
