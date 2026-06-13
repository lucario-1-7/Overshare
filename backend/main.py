"""FastAPI app + the single POST /analyze endpoint (PLAN §4.2).

Design rules baked in from hour 0:
  - Models load ONCE at startup (the hook is empty in Phase 1), never per-request.
  - Uploads are processed in-memory and never written to disk (meta.stored=False).
  - One endpoint accepts multipart (file) OR JSON (text/username); the router
    decides which pipelines fire.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from backend.assemble import build_report
from backend.router import run_pipelines

# Loaded-once model registry. Empty in Phase 1; populated in the lifespan below
# in later phases (YOLO / RetinaFace / PaddleOCR / Presidio onto the GPU, once).
MODELS: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Phase 2+: load the perception models here and stash handles in MODELS so they
    # are reused across requests (never reloaded per-request).
    print("[startup] Overshare ready - Phase 1 (EXIF only, no GPU models loaded yet).")
    yield
    MODELS.clear()


app = FastAPI(title="Overshare", version="0.1.0", lifespan=lifespan)

# Dev-friendly CORS so the throwaway page works even when opened from file://.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "phase": 1}


@app.get("/")
def index():
    idx = FRONTEND_DIR / "index.html"
    if idx.exists():
        return FileResponse(idx)
    return JSONResponse({"detail": "frontend/index.html not found"}, status_code=404)


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
    # Phase 2 hardening (do when heavyweight models land at this call site):
    #   - cap upload size before reading (Content-Length -> 413) to avoid OOM,
    #   - offload run_pipelines via run_in_threadpool so GPU/CPU work doesn't
    #     block the event loop. Both are cheap and unnecessary for EXIF-only.
    image_bytes, text, username = await _parse_request(request)
    signals, models_run = run_pipelines(
        image_bytes=image_bytes, text=text, username=username
    )
    report = build_report(signals, models_run)
    # image_bytes goes out of scope here — nothing is persisted.
    # mode="json" + the Evidence.raw validator guarantee a serializable payload
    # no matter what a future extractor stuffs into evidence.raw.
    return JSONResponse(report.model_dump(mode="json"))
