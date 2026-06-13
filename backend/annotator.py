"""Annotator (PLAN §4.6) — the "proof the AI is real" hero visual.

Reads every Signal that carries an `evidence.bbox` and draws a labelled box on a
copy of the uploaded image, returning it as a base64 PNG data URL for the report's
`annotatedImage` field. Signals with no bbox (EXIF gps/device, future PII) are
ignored here — they surface as chips, not boxes.

PIL-only by design: no torch/numpy, so this works in the light venv too. If there
are no boxable signals (a clean photo, or text/username input), it returns None and
the UI just shows the original upload — "honest when clean".
"""
from __future__ import annotations

import base64
from io import BytesIO
from typing import List, Optional, Sequence

from backend.contracts.signal import Signal

# Stable per-type box colors so the same signal type always reads the same in the UI.
_COLORS = {
    "face": (255, 64, 129),          # pink
    "person": (0, 200, 255),         # cyan
    "home_indicator": (124, 252, 0), # green
    "document": (255, 193, 7),       # amber
    "screen_text": (171, 71, 188),   # purple
}
_DEFAULT_COLOR = (255, 255, 255)


def _font():
    """A small bitmap font that's always available (no external font files)."""
    try:
        from PIL import ImageFont

        return ImageFont.load_default()
    except Exception:
        return None


def _text_size(draw, text: str, font) -> tuple[int, int]:
    """Measure text across Pillow versions (textbbox is the modern API)."""
    try:
        l, t, r, b = draw.textbbox((0, 0), text, font=font)
        return r - l, b - t
    except Exception:
        try:
            return draw.textsize(text, font=font)
        except Exception:
            return (len(text) * 6, 11)


def annotate(image_bytes: bytes, signals: Sequence[Signal]) -> Optional[str]:
    """Draw labelled boxes for every bbox-bearing signal. Returns a PNG data URL,
    or None when there's nothing visual to draw / the image can't be decoded."""
    if not image_bytes:
        return None
    boxed: List[Signal] = [
        s for s in signals if s.evidence and s.evidence.bbox and len(s.evidence.bbox) == 4
    ]
    if not boxed:
        return None  # nothing to annotate — UI falls back to the raw upload

    try:
        from PIL import Image, ImageDraw

        img = Image.open(BytesIO(image_bytes)).convert("RGB")
    except Exception:
        return None

    draw = ImageDraw.Draw(img)
    font = _font()
    W, H = img.size
    # Scale line/label with image size so boxes are visible on big photos.
    line_w = max(2, round(min(W, H) / 300))

    for s in boxed:
        try:
            x, y, w, h = (float(v) for v in s.evidence.bbox)
        except Exception:
            continue
        # Clamp to the image so a slightly-oversized box can't error or draw off-canvas.
        x1 = max(0, min(x, W - 1))
        y1 = max(0, min(y, H - 1))
        x2 = max(0, min(x + w, W - 1))
        y2 = max(0, min(y + h, H - 1))
        if x2 <= x1 or y2 <= y1:
            continue
        color = _COLORS.get(s.type, _DEFAULT_COLOR)
        draw.rectangle([x1, y1, x2, y2], outline=color, width=line_w)

        label = f"{s.type}: {s.value}"
        if len(label) > 40:
            label = label[:39] + "…"
        tw, th = _text_size(draw, label, font)
        # Label chip above the box, flipping below if it would clip the top edge.
        ly = y1 - th - 4
        if ly < 0:
            ly = y1 + 2
        # Clamp horizontally so a box near the right edge doesn't draw its label
        # off-canvas (Pillow would silently truncate it — exactly on the most
        # interesting edge detections).
        lx = max(0, min(x1, W - (tw + 6)))
        draw.rectangle([lx, ly, lx + tw + 6, ly + th + 4], fill=color)
        draw.text((lx + 3, ly + 2), label, fill=(0, 0, 0), font=font)

    buf = BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"
