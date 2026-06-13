"""Generate JPEGs with / without EXIF for smoke-testing the EXIF pipeline.

Run directly to drop test_gps.jpg + test_clean.jpg in the cwd, or import
make_gps_jpeg()/make_clean_jpeg() to get bytes in-memory.
"""
from __future__ import annotations

from io import BytesIO

import piexif
from PIL import Image


def _deg_to_dms_rational(deg: float):
    """Decimal degrees -> EXIF ((d,1),(m,1),(s,100)) rational triple.

    Computes total hundredth-seconds once and carries, so seconds stay < 60
    (a naive floor-minutes / round-seconds split can emit s == 6000).
    """
    deg = abs(deg)
    d = int(deg)
    total_cs = round((deg - d) * 3600.0 * 100)  # hundredths of a second
    m, rem_cs = divmod(total_cs, 60 * 100)
    return ((d, 1), (m, 1), (rem_cs, 100))


def make_gps_jpeg(
    lat: float = 12.971600,
    lon: float = 77.594600,
    make: str = "TestCam",
    model: str = "Pixel-Sim",
    dt: str = "2024:01:15 14:30:00",
) -> bytes:
    """A tiny JPEG carrying GPS + Make/Model + DateTimeOriginal."""
    gps = {
        piexif.GPSIFD.GPSLatitudeRef: ("N" if lat >= 0 else "S"),
        piexif.GPSIFD.GPSLatitude: _deg_to_dms_rational(lat),
        piexif.GPSIFD.GPSLongitudeRef: ("E" if lon >= 0 else "W"),
        piexif.GPSIFD.GPSLongitude: _deg_to_dms_rational(lon),
    }
    zeroth = {
        piexif.ImageIFD.Make: make,
        piexif.ImageIFD.Model: model,
        piexif.ImageIFD.DateTime: dt,
    }
    exif_ifd = {piexif.ExifIFD.DateTimeOriginal: dt}
    exif_bytes = piexif.dump({"0th": zeroth, "Exif": exif_ifd, "GPS": gps})

    img = Image.new("RGB", (64, 64), (120, 120, 120))
    buf = BytesIO()
    img.save(buf, format="JPEG", exif=exif_bytes)
    return buf.getvalue()


def make_clean_jpeg() -> bytes:
    """A JPEG with no EXIF at all -> should yield zero signals."""
    img = Image.new("RGB", (64, 64), (10, 10, 10))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


if __name__ == "__main__":
    with open("test_gps.jpg", "wb") as f:
        f.write(make_gps_jpeg())
    with open("test_clean.jpg", "wb") as f:
        f.write(make_clean_jpeg())
    print("wrote test_gps.jpg + test_clean.jpg")
