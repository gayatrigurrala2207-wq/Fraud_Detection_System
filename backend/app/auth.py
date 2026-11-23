"""Local authentication: scrypt password hashes, server-side sessions, and roles.

Accounts live in their own SQLite file (data/auth/users.sqlite) so rebuilding the
replay database never deletes them. Session tokens are random, sent only in an
HttpOnly SameSite=Lax cookie, and stored server-side as SHA-256 hashes.
"""

from collections import defaultdict, deque
from contextlib import closing
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
import secrets
import sqlite3
import threading
import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from app.config import Settings, get_settings
from app.db import connect, now

ROLES = ("viewer", "analyst", "admin")
RANK = {role: index for index, role in enumerate(ROLES)}
SESSION_COOKIE = "fraudshield_session"
SESSION_HOURS = 12
MIN_PASSWORD_LENGTH = 10
MAX_FAILURES, FAILURE_WINDOW_SECONDS = 5, 15 * 60

AUTH_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL COLLATE NOCASE,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('viewer', 'analyst', 'admin')),
    password_hash TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    last_login_at TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_sessions_user ON sessions (user_id);
"""
PUBLIC_FIELDS = ("id", "username", "display_name", "role", "active", "created_at", "last_login_at")

# Hash of a random password, used to keep login timing similar for unknown usernames.
_DUMMY_HASH: str | None = None
_failures: dict[str, deque] = defaultdict(deque)
_failures_lock = threading.Lock()


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt$16384$8$1${salt.hex()}${key.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, key = stored.split("$")
        candidate = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p),
                                   dklen=len(key) // 2)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(candidate.hex(), key)


def dummy_verify(password: str) -> None:
    global _DUMMY_HASH
    _DUMMY_HASH = _DUMMY_HASH or hash_password(secrets.token_hex(16))
    verify_password(password, _DUMMY_HASH)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def auth_connect(config: Settings) -> sqlite3.Connection:
    path = config.auth_db_path
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
    connection = connect(path)
    connection.executescript(AUTH_SCHEMA)
    return connection


def public_user(row: sqlite3.Row) -> dict:
    user = {field: row[field] for field in PUBLIC_FIELDS}
    user["active"] = bool(user["active"])
    return user


def check_rate_limit(key: str) -> None:
    with _failures_lock:
        attempts = _failures[key]
        cutoff = time.monotonic() - FAILURE_WINDOW_SECONDS
        while attempts and attempts[0] < cutoff:
            attempts.popleft()
        if len(attempts) >= MAX_FAILURES:
            raise HTTPException(status_code=429, detail="Too many failed sign-in attempts. Try again in 15 minutes.")


def record_failure(key: str) -> None:
    with _failures_lock:
        _failures[key].append(time.monotonic())


def clear_failures(key: str) -> None:
    with _failures_lock:
        _failures.pop(key, None)


def create_session(db: sqlite3.Connection, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)
    db.execute("DELETE FROM sessions WHERE expires_at <= ?", (now(),))
    db.execute("INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
               (token_hash(token), user_id, now(), expires.isoformat(timespec="milliseconds")))
    db.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now(), user_id))
    db.commit()
    return token


def current_user(request: Request, config: Annotated[Settings, Depends(get_settings)]) -> dict:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Sign in required.")
    with closing(auth_connect(config)) as db:
        row = db.execute(
            """SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id
               WHERE s.token_hash = ? AND s.expires_at > ? AND u.active = 1""",
            (token_hash(token), now())).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="Your session has expired. Sign in again.")
    return public_user(row)


def require_role(minimum: str):
    def dependency(user: Annotated[dict, Depends(current_user)]) -> dict:
        if RANK[user["role"]] < RANK[minimum]:
            raise HTTPException(status_code=403, detail=f"This action requires the {minimum} role.")
        return user
    dependency.__name__ = f"require_{minimum}"
    return dependency


CurrentUser = Annotated[dict, Depends(current_user)]
AnalystUser = Annotated[dict, Depends(require_role("analyst"))]
AdminUser = Annotated[dict, Depends(require_role("admin"))]
