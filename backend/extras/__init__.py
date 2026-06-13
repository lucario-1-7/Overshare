"""Overshare — EXTRAS (additive, opt-in).

Digital-footprint intelligence built from external online-identity sources
(breach exposure, cross-platform presence, email domain, Gravatar). This package
is **fully isolated**: it has its own models, collectors, scoring, and a separate
`/extras/footprint` endpoint. It does NOT touch the frozen Signal/Report contracts
or the core `/analyze` pipeline — the original product keeps working exactly as-is.

All external calls are free + key-free, bounded by short timeouts, never raise, and
fall back to canned demo data so a live demo can't hang.
"""
