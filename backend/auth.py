"""
Admin authentication: username/password from env, session cookie.

When ADMIN_USERNAME and ADMIN_PASSWORD are both set, all /api/admin/* routes
(except /api/admin/login, /api/admin/logout, /api/admin/me) require a valid session.
Session is a signed cookie set after successful login.
"""
import base64
import hmac
import hashlib
import json
import os
import time
from typing import Tuple

# Cookie name and max age (seconds)
ADMIN_SESSION_COOKIE = "admin_session"
ADMIN_SESSION_MAX_AGE = 24 * 3600  # 24 hours


def _env(key: str) -> str:
    return (os.getenv(key) or "").strip()


def get_admin_credentials() -> Tuple[str | None, str | None]:
    """Return (ADMIN_USERNAME, ADMIN_PASSWORD) from env. Either can be None if unset."""
    user = _env("ADMIN_USERNAME")
    pw = _env("ADMIN_PASSWORD")
    return (user or None, pw or None)


def is_admin_protected() -> bool:
    """True if both ADMIN_USERNAME and ADMIN_PASSWORD are set (admin area is protected)."""
    user, pw = get_admin_credentials()
    return bool(user and pw)


def _session_secret() -> str:
    """Secret used to sign the session cookie. Prefer ADMIN_SESSION_SECRET; fallback to ADMIN_PASSWORD."""
    s = _env("ADMIN_SESSION_SECRET")
    if s:
        return s
    return _env("ADMIN_PASSWORD") or "dev-secret-change-in-production"


def _sign(payload: str) -> str:
    sig = hmac.new(
        _session_secret().encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return payload + "." + sig


def _verify_signed(signed: str) -> str | None:
    if "." not in signed:
        return None
    payload, sig = signed.rsplit(".", 1)
    expected = hmac.new(
        _session_secret().encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    return payload


def create_session_token() -> str:
    """Create a signed session token (payload: exp timestamp). Call after validating password."""
    exp = int(time.time()) + ADMIN_SESSION_MAX_AGE
    payload_b64 = base64.urlsafe_b64encode(json.dumps({"exp": exp, "admin": True}).encode()).decode()
    return _sign(payload_b64)


def verify_session_token(token: str) -> bool:
    """Verify the session token: signature valid and not expired."""
    payload_b64 = _verify_signed(token)
    if not payload_b64:
        return False
    try:
        data = json.loads(base64.urlsafe_b64decode(payload_b64.encode()).decode())
        if not data.get("admin"):
            return False
        exp = data.get("exp", 0)
        return exp >= int(time.time())
    except Exception:
        return False
