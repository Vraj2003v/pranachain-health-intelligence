"""Password hashing, login sessions (random token in an httpOnly cookie, only its hash is stored) and login throttling."""
import hashlib
import hmac
import re
import secrets
import time

from fastapi import HTTPException, Request, Response

from .db import db

COOKIE = "pp_session"
SESSION_DAYS = 7
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_fails: dict[str, list[float]] = {}


def hash_password(password: str, salt: bytes | None = None):
    salt = salt or secrets.token_bytes(16)
    return hashlib.scrypt(password.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32).hex(), salt.hex()


def verify_password(password: str, pw_hash: str, salt_hex: str) -> bool:
    return hmac.compare_digest(hash_password(password, bytes.fromhex(salt_hex))[0], pw_hash)


def throttled(email: str) -> bool:
    now = time.time()
    recent = [t for t in _fails.get(email, []) if now - t < 900]
    _fails[email] = recent
    return len(recent) >= 5


def note_failure(email: str):
    _fails.setdefault(email, []).append(time.time())


def clear_failures(email: str):
    _fails.pop(email, None)


def start_session(response: Response, request: Request, user_id: int):
    token = secrets.token_urlsafe(32)
    with db() as con:
        con.execute("INSERT INTO sessions(token_hash, user_id, expires_at) VALUES (?,?,datetime('now', ?))",
                    (hashlib.sha256(token.encode()).hexdigest(), user_id, f"+{SESSION_DAYS} days"))
    secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    response.set_cookie(COOKIE, token, max_age=SESSION_DAYS * 86400, httponly=True, samesite="lax", secure=secure, path="/")


def end_session(response: Response, request: Request):
    token = request.cookies.get(COOKIE)
    if token:
        with db() as con:
            con.execute("DELETE FROM sessions WHERE token_hash = ?", (hashlib.sha256(token.encode()).hexdigest(),))
    response.delete_cookie(COOKIE, path="/")


def current_user(request: Request):
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(401, "Please sign in.")
    with db() as con:
        row = con.execute(
            "SELECT u.id, u.email, u.name, u.role FROM sessions s JOIN users u ON u.id = s.user_id "
            "WHERE s.token_hash = ? AND s.expires_at > datetime('now')", (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
    if not row:
        raise HTTPException(401, "Your session has expired. Please sign in again.")
    return dict(row)


def log(user, action, detail=""):
    with db() as con:
        con.execute("INSERT INTO audit(user_id, email, action, detail) VALUES (?,?,?,?)",
                    (user["id"] if user else None, user["email"] if user else None, action, detail[:300]))
