r"""Phase 2 acceptance test — vision perception + annotator (PLAN hours 4-8).

Two tiers, so this is meaningful in BOTH venvs:

  * Light tier (always runs, needs only Pillow):
      - the Annotator draws boxes from bbox-bearing signals and returns a valid PNG;
      - graceful degradation — with no models loaded, the image path still returns
        EXIF-only signals and never crashes ("reliability first").

  * Heavy tier (runs only when ultralytics + facexlib import — i.e. in .venv-ml):
      - models load, real inference runs end-to-end through /analyze without error,
      - the report stays schema-valid and modelsRun reflects what executed.

    Set OVERSHARE_TEST_IMAGE=<path to a real photo with a face/objects> to also
    assert that detections actually fire. Without it the heavy tier only proves the
    pipeline runs clean (synthetic images rarely contain detectable faces/objects).

Run:  .\.venv-ml\Scripts\python.exe -m scripts.phase2_test
"""

from __future__ import annotations

import base64
import os
import sys
from io import BytesIO

from backend.annotator import annotate
from backend.contracts.signal import Evidence, Signal
from backend.router import run_pipelines
from scripts.make_test_image import make_clean_jpeg, make_gps_jpeg


def _decode_data_url(data_url: str) -> bytes:
    assert data_url.startswith("data:image/png;base64,"), data_url[:40]
    return base64.b64decode(data_url.split(",", 1)[1])


def test_annotator_draws_boxes() -> None:
    """Synthetic bbox signals -> a valid PNG of the same size, with pixels changed."""
    from PIL import Image

    img_bytes = make_clean_jpeg()  # 64x64 solid dark image
    orig = Image.open(BytesIO(img_bytes)).convert("RGB")

    sigs = [
        Signal(
            type="face",
            value="face 1 of 1",
            source="retinaface",
            confidence=0.99,
            evidence=Evidence(bbox=[8, 8, 24, 24]),
        ),
        Signal(
            type="home_indicator",
            value="bed",
            source="yolo",
            confidence=0.8,
            evidence=Evidence(bbox=[30, 30, 20, 20]),
        ),
        # A signal with NO bbox must be ignored by the annotator (EXIF-style).
        Signal(type="gps", value="12.97,77.59", source="exif", confidence=0.99),
    ]
    data_url = annotate(img_bytes, sigs)
    assert data_url is not None, "annotator should produce an image when bboxes exist"
    out = Image.open(BytesIO(_decode_data_url(data_url))).convert("RGB")
    assert out.size == orig.size, f"size changed: {orig.size} -> {out.size}"
    assert out.tobytes() != orig.tobytes(), "boxes were not drawn"
    print("Annotator -> valid PNG, boxes drawn, size preserved, no-bbox signal ignored. [OK]")


def test_annotator_clean_returns_none() -> None:
    """No bbox-bearing signals -> None (UI shows the raw upload). 'Honest when clean'."""
    sigs = [Signal(type="gps", value="12.97,77.59", source="exif", confidence=0.99)]
    assert annotate(make_gps_jpeg(), sigs) is None
    assert annotate(b"", sigs) is None  # no image bytes
    print("Annotator -> None when nothing is boxable / no image. [OK]")


def test_graceful_degradation_no_models() -> None:
    """Image path with an empty model registry: EXIF still runs, nothing crashes,
    and no perception model is falsely reported as having run."""
    signals, models_run = run_pipelines(image_bytes=make_gps_jpeg(), models={})
    types = {s.type for s in signals}
    assert "gps" in types, f"EXIF must still run with no models: {types}"
    assert "yolo" not in models_run and "retinaface" not in models_run, models_run
    assert "exif" in models_run
    print("Degradation -> no models loaded: EXIF-only, no crash, honest modelsRun. [OK]")


def _solid_jpeg(w: int, h: int, color: tuple) -> bytes:
    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (w, h), color).save(buf, format="JPEG")
    return buf.getvalue()


def test_server_behaviors() -> None:
    """Wiring that must hold in BOTH venvs (light runs EXIF-only, ml runs full):
    the upload size cap returns 413, normal requests still parse, and a burst of
    concurrent differently-sized images all return valid reports — exercising the
    threadpool offload + the shared-model inference lock (no crash, no interleave)."""
    import concurrent.futures as cf

    from fastapi.testclient import TestClient

    from backend.main import MAX_UPLOAD_BYTES, app

    with TestClient(app) as client:  # 'with' loads models once (None in light venv)
        # 1) size cap: an oversized body is rejected (Content-Length fast-path -> 413).
        big = b"x" * (MAX_UPLOAD_BYTES + 1)
        r = client.post("/analyze", files={"file": ("big.jpg", big, "image/jpeg")})
        assert r.status_code == 413, f"oversized upload should 413, got {r.status_code}"

        # 2) a normal upload still parses fine after the streaming-cap change.
        r = client.post(
            "/analyze", files={"file": ("ok.jpg", _solid_jpeg(80, 60, (20, 20, 20)), "image/jpeg")}
        )
        assert r.status_code == 200, r.text

        # 3) concurrency burst: differently-sized images in flight at once. With the
        #    per-model lock the shared YOLO/RetinaFace instances can't interleave;
        #    every request must come back a valid 200 report.
        sizes = [(320, 240), (640, 480), (200, 300), (96, 96), (512, 400), (150, 150)]
        imgs = [_solid_jpeg(w, h, ((i * 40) % 255, 70, 130)) for i, (w, h) in enumerate(sizes)]

        def _post(b: bytes):
            rr = client.post("/analyze", files={"file": ("c.jpg", b, "image/jpeg")})
            return rr.status_code, rr.json()

        with cf.ThreadPoolExecutor(max_workers=6) as ex:
            results = list(ex.map(_post, imgs))
        for sc, rep in results:
            assert sc == 200, f"concurrent request failed: {sc}"
            assert "signals" in rep and "meta" in rep, rep
        print(f"Server -> size cap 413, normal 200, {len(results)} concurrent requests OK. [OK]")


def _heavy_available() -> bool:
    try:
        import facexlib  # noqa: F401
        import ultralytics  # noqa: F401

        return True
    except Exception:
        return False


def test_heavy_pipeline_end_to_end() -> int:
    """Real model load + inference through /analyze (only when ML libs are present)."""
    if not _heavy_available():
        print("Heavy tier SKIPPED: ultralytics/facexlib not importable (light venv).")
        return 0

    from fastapi.testclient import TestClient

    from backend.main import app

    # Prefer a real photo so we assert that detections actually fire. Priority:
    #   1) OVERSHARE_TEST_IMAGE env var, 2) ultralytics' bundled zidane.jpg (people +
    #   faces, ships with the package — no network), 3) synthetic (no-crash only).
    real_source = None
    img_bytes = None
    env_img = os.environ.get("OVERSHARE_TEST_IMAGE")
    if env_img and os.path.exists(env_img):
        with open(env_img, "rb") as f:
            img_bytes = f.read()
        real_source = env_img
    else:
        try:
            from ultralytics.utils import ASSETS

            cand = ASSETS / "zidane.jpg"
            if cand.exists():
                img_bytes = cand.read_bytes()
                real_source = str(cand)
        except Exception:
            pass
    if img_bytes is None:
        img_bytes = make_gps_jpeg()
        print("Heavy tier: synthetic image (no real photo found) — no-crash check only.")
    else:
        print(f"Heavy tier: real image {real_source} — asserting detections fire.")

    with TestClient(app) as client:  # 'with' triggers lifespan -> models load once
        h = client.get("/health").json()
        print(f"  /health -> {h}")
        assert h["phase"] == 2
        r = client.post("/analyze", files={"file": ("p.jpg", img_bytes, "image/jpeg")})
        assert r.status_code == 200, r.text
        rep = r.json()
        # Report shape stays valid no matter what fired.
        for key in ("annotatedImage", "signals", "graph", "risks", "attackPath", "fixes", "meta"):
            assert key in rep, f"missing report key: {key}"
        run = rep["meta"]["modelsRun"]
        print(f"  modelsRun={run}; signals={len(rep['signals'])}")
        assert "exif" in run
        # If the models actually loaded, they should appear in modelsRun.
        assert "yolo" in run, "YOLO loaded but did not run"
        assert "retinaface" in run, "RetinaFace loaded but did not run"
        if real_source is not None:
            types = {s["type"] for s in rep["signals"]}
            assert types & {"face", "person", "home_indicator", "document"}, (
                f"real image yielded no visual detections: {types}"
            )
            assert rep["annotatedImage"], "real detections but no annotated image"
            # zidane.jpg specifically has people + faces — assert both models fired.
            if real_source.endswith("zidane.jpg"):
                assert "person" in types, f"expected YOLO 'person' on zidane.jpg: {types}"
                assert "face" in types, f"expected RetinaFace 'face' on zidane.jpg: {types}"
            print(f"  real-image detection types: {sorted(types)} [OK]")
    print("Heavy tier -> models loaded, /analyze ran clean, report valid. [OK]")
    return 0


def main() -> int:
    test_annotator_draws_boxes()
    test_annotator_clean_returns_none()
    test_graceful_degradation_no_models()
    test_server_behaviors()
    test_heavy_pipeline_end_to_end()
    print("\nAll Phase 2 assertions passed. [PASS]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
