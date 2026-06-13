"""Extras API — a SEPARATE router mounted under /extras.

Isolated from the core: `/analyze` and every existing endpoint are unchanged. This
adds an opt-in digital-footprint endpoint. Collectors run in a threadpool so their
(sync) HTTP calls never block the event loop, and everything degrades gracefully.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .collectors import collect
from .footprint import build_footprint

router = APIRouter(prefix="/extras", tags=["extras: digital footprint"])


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
