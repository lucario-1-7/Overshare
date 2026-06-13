"""FastAPI app + the single POST /analyze endpoint (PLAN §4.2).

Design rules baked in from hour 0:
  - Models load ONCE at startup (lifespan), never per-request, onto the GPU.
  - Uploads are processed in-memory and never written to disk (meta.stored=False).
  - One endpoint accepts multipart (file) OR JSON (text/username); the router
    decides which pipelines fire.

Phase 2 also lands the two hardening items deferred from Phase 1 now that heavy
models run per request: an upload-size cap (reject huge bodies with 413 before
reading → no OOM) and a threadpool offload (GPU/CPU inference must not block the
async event loop).
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from backend.annotator import annotate
from backend.assemble import build_report
from backend.explain import generate_explanation
from backend.router import run_pipelines

# Loaded-once model registry (PLAN §4.2): perception weights live here for the app's
# lifetime and are reused across requests, never reloaded. Empty until the lifespan
# below populates it; in the light venv (no torch) the loaders return None and the
# server still boots and serves EXIF-only — reliability first.
MODELS: dict = {}

# Reject request bodies larger than this before reading them (deferred Phase-1 item:
# avoids decoding an attacker-sized upload into memory).
MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB


def _pick_device() -> str:
    """'cuda' if a torch CUDA device is available, else 'cpu'. Safe in the light venv."""
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


@asynccontextmanager
async def lifespan(app: FastAPI):
    from backend.pipelines.faces import load_face_model
    from backend.pipelines.loaders import load_phase3_models
    from backend.pipelines.objects import load_yolo_model

    device = _pick_device()
    MODELS["device"] = device
    MODELS["cuda_available"] = device == "cuda"
    MODELS["yolo"] = load_yolo_model(device)
    MODELS["face"] = load_face_model(device)
    # Phase 3 fills these (PaddleOCR, Presidio) inside its own loaders module — no
    # edits to this file required. No-ops until Phase 3 lands.
    load_phase3_models(MODELS, device)
    loaded = [k for k in ("yolo", "face", "ocr", "pii") if MODELS.get(k) is not None]
    print(
        f"[startup] Overshare ready. device={device}; "
        f"models loaded: {loaded or 'none (EXIF-only)'}"
    )
    yield
    MODELS.clear()


app = FastAPI(title="Overshare", version="0.2.0", lifespan=lifespan)

# Dev-friendly CORS so the throwaway page works even when opened from file://.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ADDITIVE: isolated "extras" module (digital-footprint intelligence) ---------
# Mounts an opt-in /extras/footprint endpoint. Does NOT alter /analyze or any core
# behavior, and is wrapped so a broken/absent extras package can never break the app.
try:
    from backend.extras.api import router as extras_router

    app.include_router(extras_router)
    print("[extras] digital-footprint module mounted at /extras")
except Exception as _e:  # noqa: BLE001 — extras must never take down the core API
    print(f"[extras] not mounted ({type(_e).__name__}: {_e}); core API unaffected.")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/health")
def health() -> dict:
    # `cuda_available` lets a probe tell an intentional EXIF-only boot (no torch /
    # no GPU) apart from a GPU box where models silently failed to load.
    return {
        "status": "ok",
        "phase": 2,
        "device": MODELS.get("device", "cpu"),
        "cuda_available": MODELS.get("cuda_available", False),
        "models": [k for k in ("yolo", "face") if MODELS.get(k) is not None],
    }


@app.get("/")
def index():
    idx = FRONTEND_DIR / "index.html"
    if idx.exists():
        return FileResponse(idx)
    return JSONResponse({"detail": "frontend/index.html not found"}, status_code=404)


# Golden, fully-populated Report fixture (signals + graph + risks + attackPath + fixes).
# Lets the Phase 5 frontend develop against a real endpoint before Phase 3/4 land, and
# serves as the canonical example of the frozen Report contract (PLAN §4.12).
_SAMPLE_REPORT = Path(__file__).resolve().parent.parent / "fixtures" / "report_sample.json"


@app.get("/sample-report")
def sample_report():
    if _SAMPLE_REPORT.exists():
        return JSONResponse(json.loads(_SAMPLE_REPORT.read_text(encoding="utf-8")))
    return JSONResponse({"detail": "fixtures/report_sample.json not found"}, status_code=404)


async def _parse_request(request: Request):
    """Pull image bytes / text / username out of either a multipart or JSON body."""
    ct = request.headers.get("content-type", "")
    image_bytes = None
    text = None
    username = None

    if "application/json" in ct:
        try:
            body = await request.json()
        except Exception:
            body = {}
        text = (body or {}).get("text") or None
        username = (body or {}).get("username") or None
    else:
        # multipart/form-data (and a tolerant fallback for anything form-like)
        try:
            form = await request.form()
            upload = form.get("file")
            if upload is not None and hasattr(upload, "read"):
                image_bytes = await upload.read()
            text = (form.get("text") or None)
            username = (form.get("username") or None)
        except Exception:
            pass

    return image_bytes, text, username


@app.post("/analyze")
async def analyze(request: Request):
    too_large = JSONResponse(
        {"detail": f"Upload too large (max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB)."},
        status_code=413,
    )
    # Fast path: reject an honest oversized upload before reading anything.
    try:
        clen = int(request.headers.get("content-length", "0") or "0")
    except ValueError:
        clen = 0
    if clen > MAX_UPLOAD_BYTES:
        return too_large

    # Enforce the cap while STREAMING the body, before it is buffered/parsed. This
    # closes two holes a Content-Length-only check leaves open: a chunked-transfer
    # request (no Content-Length) and a giant JSON `text` body — both would otherwise
    # be read fully into RAM. We cache the capped bytes on the request so the
    # downstream .form()/.json() parse reuses them instead of re-reading the stream.
    buf = bytearray()
    try:
        async for chunk in request.stream():
            buf += chunk
            if len(buf) > MAX_UPLOAD_BYTES:
                return too_large
    except Exception:
        buf = bytearray()
    request._body = bytes(buf)  # Starlette: a set _body short-circuits stream()/body()

    image_bytes, text, username = await _parse_request(request)

    # Offload the perception work to a worker thread: model inference is sync and
    # CPU/GPU-bound, so running it inline would block the event loop for other requests.
    signals, models_run = await run_in_threadpool(
        run_pipelines, image_bytes, text, username, MODELS
    )
    annotated_image = None
    if image_bytes:
        annotated_image = await run_in_threadpool(annotate, image_bytes, signals)

    report = build_report(signals, models_run, annotated_image)
    # Phase 7 (PLAN §4.11): optional local-LLM explanation — additive + NON-BLOCKING.
    # Offloaded so the sync HTTP call to Ollama can't block the event loop; returns
    # None fast if Ollama is down/absent, so the report always ships either way.
    report.explanation = await run_in_threadpool(generate_explanation, report)
    # image_bytes goes out of scope here — nothing is persisted (meta.stored=False).
    # mode="json" + the Evidence.raw validator guarantee a serializable payload
    # no matter what an extractor stuffs into evidence.raw.
    return JSONResponse(report.model_dump(mode="json"))
