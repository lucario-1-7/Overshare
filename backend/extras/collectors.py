"""External footprint collectors — free, key-free, demo-safe.

Each collector: lazy-imports requests, bounds every call with a short timeout,
NEVER raises (returns [] on any error), and a canned fallback (env OVERSHARE_CANNED=1
or a known demo identifier) keeps a live demo from hanging or coming back empty.

Sources (all free, no key, no card):
  - breach exposure  -> XposedOrNot   (GET /v1/check-email/{email})
  - platform presence-> curated GET 200/404 on GitHub / Reddit / GitLab / dev.to
  - email domain     -> personal vs corporate (no network)
  - Gravatar         -> email -> public profile/avatar existence
"""
from __future__ import annotations

import hashlib
import os
from typing import List, Optional

from .models import FootprintSignal

_TIMEOUT = 4.0
_UA = {"User-Agent": "Overshare-Extras/1.0 (privacy self-audit)"}

_FREEMAIL = {
    "gmail.com", "googlemail.com", "yahoo.com", "ymail.com", "outlook.com",
    "hotmail.com", "live.com", "msn.com", "icloud.com", "me.com", "mac.com",
    "proton.me", "protonmail.com", "pm.me", "aol.com", "gmx.com", "zoho.com",
    "mail.com", "yandex.com", "tutanota.com",
}

# Only reliably-checkable platforms (clean 200/404). LinkedIn/Instagram/X are
# login-walled and would false-positive, so they're intentionally excluded.
_PRESENCE_SITES = [
    ("github", "https://github.com/{u}"),
    ("reddit", "https://www.reddit.com/user/{u}/about.json"),
    ("gitlab", "https://gitlab.com/{u}"),
    ("devto", "https://dev.to/{u}"),
]

# Canned demo data (used under OVERSHARE_CANNED=1 or for these known handles) so the
# live demo always produces a rich, reproducible result.
_CANNED_USER = {
    "torvalds": [("github", "https://github.com/torvalds"), ("gitlab", "https://gitlab.com/torvalds")],
    "demo": [("github", "https://github.com/demo"), ("reddit", "https://reddit.com/user/demo"),
             ("gitlab", "https://gitlab.com/demo"), ("devto", "https://dev.to/demo")],
}
_CANNED_BREACH = {"demo@overshare.app": ["Adobe", "Canva", "LinkedIn", "Dropbox"]}


def _requests():
    try:
        import requests  # lazy — keeps the light venv importable
        return requests
    except Exception:
        return None


def _canned_on() -> bool:
    return os.environ.get("OVERSHARE_CANNED") == "1"


# --- email domain: personal vs corporate (no network) ---------------------------
def classify_email_domain(email: str) -> List[FootprintSignal]:
    if not email or "@" not in email:
        return []
    domain = email.strip().lower().rsplit("@", 1)[-1]
    if not domain:
        return []
    kind = "personal" if domain in _FREEMAIL else "corporate"
    out = [FootprintSignal(type="email_domain", value=kind, source="domain",
                           detail={"domain": domain})]
    if kind == "corporate":
        org = domain.rsplit(".", 1)[0].split(".")[-1]  # acme.com -> acme
        out.append(FootprintSignal(type="organization", value=org.title(), source="domain",
                                   detail={"domain": domain, "inferred": True}))
    return out


# --- breach exposure: XposedOrNot (free, no key) ---------------------------------
def check_breaches(email: str) -> List[FootprintSignal]:
    if not email or "@" not in email:
        return []
    if _canned_on() or email.strip().lower() in _CANNED_BREACH:
        names = _CANNED_BREACH.get(email.strip().lower(), ["Adobe", "Canva", "LinkedIn"])
        return [FootprintSignal(type="breach_exposure", value=f"{len(names)} breaches",
                                source="xposedornot", detail={"count": len(names), "names": names, "canned": True})]
    requests = _requests()
    if requests is None:
        return []
    try:
        r = requests.get(f"https://api.xposedornot.com/v1/check-email/{email.strip()}",
                         headers=_UA, timeout=_TIMEOUT)
        if r.status_code != 200:
            return []
        raw = (r.json() or {}).get("breaches")
        names: List[str] = []
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, list):
                    names.extend(str(x) for x in item if x)
                elif isinstance(item, str):
                    names.append(item)
        names = [n for n in names if n]
        if not names:
            return []
        return [FootprintSignal(type="breach_exposure", value=f"{len(names)} breaches",
                                source="xposedornot", detail={"count": len(names), "names": names[:20]})]
    except Exception:
        return []


# --- Gravatar: email -> public profile/avatar existence (free, no key) -----------
def check_gravatar(email: str) -> List[FootprintSignal]:
    if not email or "@" not in email:
        return []
    if _canned_on():
        return [FootprintSignal(type="gravatar_profile", value="public Gravatar profile",
                                source="gravatar", detail={"canned": True})]
    requests = _requests()
    if requests is None:
        return []
    h = hashlib.md5(email.strip().lower().encode("utf-8")).hexdigest()
    try:
        r = requests.get(f"https://www.gravatar.com/{h}.json", headers=_UA, timeout=_TIMEOUT)
        if r.status_code == 200:
            name = None
            try:
                entry = (r.json().get("entry") or [{}])[0]
                name = (entry.get("displayName") or (entry.get("name") or {}).get("formatted"))
            except Exception:
                name = None
            return [FootprintSignal(type="gravatar_profile", value=name or "public Gravatar profile",
                                    source="gravatar", detail={"url": f"https://gravatar.com/{h}"})]
        return []
    except Exception:
        return []


# --- platform presence: curated reliable sites ----------------------------------
def check_presence(username: str) -> List[FootprintSignal]:
    if not username or not username.strip():
        return []
    handle = username.strip().lstrip("@")
    if "@" in handle:
        handle = handle.split("@", 1)[0]
    if not (1 <= len(handle) <= 39 and all(c.isalnum() or c in "-_." for c in handle)):
        return []

    if _canned_on() or handle.lower() in _CANNED_USER:
        hits = _CANNED_USER.get(handle.lower(), _CANNED_USER["demo"])
        return [FootprintSignal(type="platform_presence", value=f"{handle} ({site})",
                                source="presence", detail={"site": site, "url": url, "canned": True})
                for site, url in hits]

    requests = _requests()
    if requests is None:
        return []
    out: List[FootprintSignal] = []
    for site, template in _PRESENCE_SITES:
        url = template.format(u=handle)
        try:
            resp = requests.get(url, headers=_UA, timeout=_TIMEOUT, allow_redirects=True)
            if resp.status_code == 200:
                profile = url.replace("/about.json", "")
                out.append(FootprintSignal(type="platform_presence", value=f"{handle} ({site})",
                                           source="presence", detail={"site": site, "url": profile}))
        except Exception:
            continue
    return out


def collect(email: Optional[str] = None, username: Optional[str] = None) -> List[FootprintSignal]:
    """Run every applicable collector and return the combined footprint signals."""
    signals: List[FootprintSignal] = []
    if email:
        signals += classify_email_domain(email)
        signals += check_breaches(email)
        signals += check_gravatar(email)
    if username:
        signals += check_presence(username)
    return signals
