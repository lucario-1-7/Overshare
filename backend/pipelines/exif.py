"""EXIF pipeline (PLAN §4.4) — the cheapest model, used to prove the spine first.

Reads image bytes with Pillow and emits:
  - `gps`       : "lat,lon" in decimal degrees (from GPSInfo IFD)
  - `device`    : "Make Model" (camera/phone that took the shot)
  - `timestamp` : capture time (DateTimeOriginal, falling back to DateTime)

Robust by design: any missing/garbled tag is skipped, never raised. A clean
image simply yields no signals ("honest when clean").
"""
from __future__ import annotations

from io import BytesIO
from typing import List, Optional

from PIL import ExifTags, Image

from backend.contracts.signal import Evidence, Signal

# EXIF tag ids we care about (avoids name-lookup fragility across Pillow versions).
_TAG_MAKE = 0x010F
_TAG_MODEL = 0x0110
_TAG_DATETIME = 0x0132          # in the base IFD
_TAG_DATETIME_ORIGINAL = 0x9003  # in the Exif IFD

# GPSInfo sub-IFD tag ids.
_GPS_LAT_REF = 1
_GPS_LAT = 2
_GPS_LON_REF = 3
_GPS_LON = 4


def _clean_str(v) -> str:
    """Decode bytes, drop trailing NULs/whitespace that EXIF strings often carry."""
    if isinstance(v, bytes):
        v = v.decode("utf-8", "ignore")
    return str(v).replace("\x00", "").strip()


def _to_float(x) -> Optional[float]:
    """Handle IFDRational, (num, den) tuples, and plain numbers."""
    try:
        return float(x)
    except (TypeError, ValueError):
        try:
            num, den = x
            return float(num) / float(den) if den else None
        except Exception:
            return None


def _dms_to_decimal(dms, ref) -> Optional[float]:
    """Convert (deg, min, sec) + N/S/E/W reference into signed decimal degrees."""
    try:
        d = _to_float(dms[0])
        m = _to_float(dms[1])
        s = _to_float(dms[2])
    except (TypeError, IndexError):
        return None
    if d is None or m is None or s is None:
        return None
    dec = d + m / 60.0 + s / 3600.0
    ref = _clean_str(ref).upper()
    if ref in ("S", "W"):
        dec = -dec
    return round(dec, 6)


def extract_exif_signals(image_bytes: bytes) -> List[Signal]:
    signals: List[Signal] = []
    try:
        img = Image.open(BytesIO(image_bytes))
        exif = img.getexif()
    except Exception:
        return signals
    if not exif:
        return signals

    # --- device (make/model) ---
    make = _clean_str(exif.get(_TAG_MAKE, ""))
    model = _clean_str(exif.get(_TAG_MODEL, ""))
    device = " ".join(p for p in (make, model) if p).strip()
    if device:
        signals.append(
            Signal(
                type="device",
                value=device,
                source="exif",
                confidence=0.9,
                evidence=Evidence(raw={"make": make, "model": model}),
            )
        )

    # --- timestamp (DateTimeOriginal preferred, else DateTime) ---
    dt = ""
    try:
        exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
        dt = _clean_str(exif_ifd.get(_TAG_DATETIME_ORIGINAL, "")) if exif_ifd else ""
    except Exception:
        dt = ""
    if not dt:
        dt = _clean_str(exif.get(_TAG_DATETIME, ""))
    if dt:
        signals.append(
            Signal(type="timestamp", value=dt, source="exif", confidence=0.9)
        )

    # --- gps ---
    gps_ifd = {}
    try:
        gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo) or {}
    except Exception:
        gps_ifd = {}
    if gps_ifd:
        lat = _dms_to_decimal(gps_ifd.get(_GPS_LAT), gps_ifd.get(_GPS_LAT_REF))
        lon = _dms_to_decimal(gps_ifd.get(_GPS_LON), gps_ifd.get(_GPS_LON_REF))
        if lat is not None and lon is not None:
            signals.append(
                Signal(
                    type="gps",
                    value=f"{lat},{lon}",
                    source="exif",
                    confidence=0.99,
                    evidence=Evidence(
                        raw={"lat": lat, "lon": lon},
                        text=f"{lat}, {lon}",
                    ),
                )
            )

    return signals
