"""Extras API — a SEPARATE router mounted under /extras.

Isolated from the core: `/analyze` and every existing endpoint are unchanged. This
adds an opt-in digital-footprint endpoint. Collectors run in a threadpool so their
(sync) HTTP calls never block the event loop, and everything degrades gracefully.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .collectors import collect
from .footprint import build_footprint
from .pattern import build_profile

router = APIRouter(prefix="/extras", tags=["extras: digital footprint"])

_MAX_POSTS = 25  # bound the multi-post upload


class FootprintRequest(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None


@router.get("/health")
def extras_health() -> dict:
    return {
        "status": "ok",
        "module": "extras.footprint",
        "sources": ["xposedornot (breaches)", "gravatar", "presence: github/reddit/gitlab/devto"],
        "keys_required": False,
    }


@router.post("/footprint")
async def footprint(req: FootprintRequest):
    """Build a digital-footprint report from an email and/or username."""
    if not req.email and not req.username:
        return JSONResponse({"detail": "Provide an email and/or username."}, status_code=400)
    signals = await run_in_threadpool(collect, req.email, req.username)
    report = build_footprint(req.email, req.username, signals)
    return JSONResponse(report.model_dump(mode="json"))


@router.post("/profile")
async def profile(request: Request):
    """Multi-post analysis: upload several images (form field `files`) → run the EXISTING
    core pipeline on each → aggregate into a footprint profile (Pattern Engine)."""
    # Lazy imports (at request time the core app is fully initialized → no circular import,
    # and the core modules are reused read-only — never modified).
    from backend.main import MODELS
    from backend.router import run_pipelines

    try:
        form = await request.form()
    except Exception:
        return JSONResponse({"detail": "Expected multipart form with image files."}, status_code=400)

    uploads = form.getlist("files")
    single = form.get("file")
    if single is not None:
        uploads = list(uploads) + [single]
    uploads = [u for u in uploads if u is not None and hasattr(u, "read")][:_MAX_POSTS]
    if not uploads:
        return JSONResponse({"detail": "No image files provided (field `files`)."}, status_code=400)

    posts = []
    for up in uploads:
        try:
            data = await up.read()
        except Exception:
            continue
        if not data:
            continue
        sigs, _run = await run_in_threadpool(run_pipelines, data, None, None, MODELS)
        posts.append(sigs)

    report = build_profile(posts)
    return JSONResponse(report.model_dump(mode="json"))
