"""Pre-pull every model weight so hour-18 network flakiness can't break the demo
(PLAN §7). Run this in the background early.

Each block is import-guarded: libraries from requirements-ml.txt that aren't
installed yet are skipped with a note, so this is safe to run during Phase 1
before the heavy stack lands.

    python -m scripts.download_weights
"""
from __future__ import annotations


def _try(name: str, fn) -> None:
    print(f"\n=== {name} ===")
    try:
        fn()
        print(f"[ok]   {name}")
    except ImportError as e:
        print(f"[skip] {name}: not installed ({e}). See requirements-ml.txt.")
    except Exception as e:  # noqa: BLE001 — downloads are best-effort
        print(f"[warn] {name}: {type(e).__name__}: {e}")


def dl_spacy() -> None:
    import spacy

    try:
        spacy.load("en_core_web_lg")
    except OSError:
        from spacy.cli import download

        download("en_core_web_lg")


def dl_yolo() -> None:
    from ultralytics import YOLO

    YOLO("yolov8n.pt")  # downloads weights into the ultralytics cache


def dl_retinaface() -> None:
    from retinaface.RetinaFace import build_model

    build_model()  # pulls the pretrained weights on first build


def dl_paddleocr() -> None:
    from paddleocr import PaddleOCR

    PaddleOCR(use_angle_cls=True, lang="en")  # downloads det/rec/cls models


def dl_easyocr() -> None:
    import easyocr

    easyocr.Reader(["en"])  # downloads detector + recognizer


def main() -> None:
    _try("spaCy en_core_web_lg", dl_spacy)
    _try("YOLOv8 (yolov8n.pt)", dl_yolo)
    _try("RetinaFace", dl_retinaface)
    _try("PaddleOCR", dl_paddleocr)
    _try("EasyOCR (fallback)", dl_easyocr)
    print("\nDone. Whatever downloaded is cached and reused at startup in later phases.")


if __name__ == "__main__":
    main()
