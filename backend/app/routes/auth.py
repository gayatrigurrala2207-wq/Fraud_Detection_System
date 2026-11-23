"""Sign-in, first-run setup, own account, and admin user management."""

from contextlib import closing
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field, StringConstraints

from app.auth import (
    MIN_PASSWORD_LENGTH, SESSION_COOKIE, SESSION_HOURS, AdminUser, CurrentUser, auth_connect, check_rate_limit,
    clear_failures, create_session, current_user, dummy_verify, hash_password, public_user, record_failure,
    token_hash, verify_password,
)
from app.db import now
from app.services import Config

router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])

Username = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=32,
                                            pattern=r"^[A-Za-z0-9._-]+$")]
DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
Password = Annotated[str, Field(min_length=MIN_PASSWORD_LENGTH, max_length=200)]
Role = Literal["viewer", "analyst", "admin"]


class Credentials(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=200)


class NewUser(BaseModel):
    username: Username
    display_name: DisplayName
    password: Password
    role: Role = "analyst"


class Setup(BaseModel):
    username: Username
    display_name: DisplayName
    password: Password


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: Password


class UserUpdate(BaseModel):
    display_name: DisplayName | None = None
    role: Role | None = None
    active: bool | None = None


class PasswordReset(BaseModel):
    new_password: Password


def _set_cookie(response: Response, token: str, config) -> None:
    response.set_cookie(SESSION_COOKIE, token, max_age=SESSION_HOURS * 3600, httponly=True, samesite="lax",
                        secure=config.cookie_secure, path="/")


@router.get("/status")
def status(request: Request, config: Config) -> dict:
    """Public: whether first-run setup is needed and who is signed in (if anyone)."""
    with closing(auth_connect(config)) as db:
        setup_required = db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
    user = None
    if not setup_required and request.cookies.get(SESSION_COOKIE):
        try:
            user = current_user(request, config)
        except HTTPException:
            user = None
    return {"setup_required": setup_required, "user": user, "min_password_length": MIN_PASSWORD_LENGTH}


@router.post("/setup")
def setup(request: Setup, response: Response, config: Config) -> dict:
    """Create the first administrator. Allowed only while no accounts exist."""
    with closing(auth_connect(config)) as db:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
            db.rollback()
            raise HTTPException(status_code=409, detail="Setup is already complete. Sign in instead.")
        cursor = db.execute(
            "INSERT INTO users (username, display_name, role, password_hash, created_at) VALUES (?, ?, 'admin', ?, ?)",
            (request.username, request.display_name, hash_password(request.password), now()))
        db.commit()
        token = create_session(db, cursor.lastrowid)
        user = public_user(db.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone())
    _set_cookie(response, token, config)
    return {"user": user}


@router.post("/login")
def login(credentials: Credentials, request: Request, response: Response, config: Config) -> dict:
    key = f"{credentials.username.strip().lower()}|{request.client.host if request.client else ''}"
    check_rate_limit(key)
    with closing(auth_connect(config)) as db:
        row = db.execute("SELECT * FROM users WHERE username = ?", (credentials.username.strip(),)).fetchone()
        if row is None:
            dummy_verify(credentials.password)
        if row is None or not verify_password(credentials.password, row["password_hash"]) or not row["active"]:
            record_failure(key)
            raise HTTPException(status_code=401, detail="Incorrect username or password, or the account is disabled.")
        clear_failures(key)
        token = create_session(db, row["id"])
        user = public_user(db.execute("SELECT * FROM users WHERE id = ?", (row["id"],)).fetchone())
    _set_cookie(response, token, config)
    return {"user": user}


@router.post("/logout")
def logout(request: Request, response: Response, config: Config) -> dict:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        with closing(auth_connect(config)) as db:
            db.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash(token),))
            db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
def me(user: CurrentUser) -> dict:
    return {"user": user}


@router.post("/password")
def change_password(change: PasswordChange, request: Request, response: Response, user: CurrentUser,
                    config: Config) -> dict:
    with closing(auth_connect(config)) as db:
        row = db.execute("SELECT password_hash FROM users WHERE id = ?", (user["id"],)).fetchone()
        if not verify_password(change.current_password, row["password_hash"]):
            raise HTTPException(status_code=400, detail="Current password is incorrect.")
        db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(change.new_password), user["id"]))
        db.execute("DELETE FROM sessions WHERE user_id = ?", (user["id"],))  # sign out other devices
        db.commit()
        token = create_session(db, user["id"])
    _set_cookie(response, token, config)
    return {"ok": True}


@users_router.get("")
def list_users(_: AdminUser, config: Config) -> dict:
    with closing(auth_connect(config)) as db:
        rows = db.execute("SELECT * FROM users ORDER BY active DESC, role DESC, username").fetchall()
    return {"items": [public_user(row) for row in rows]}


@users_router.post("", status_code=201)
def create_user(new: NewUser, _: AdminUser, config: Config) -> dict:
    with closing(auth_connect(config)) as db:
        if db.execute("SELECT 1 FROM users WHERE username = ?", (new.username,)).fetchone():
            raise HTTPException(status_code=409, detail="That username is already taken.")
        cursor = db.execute(
            "INSERT INTO users (username, display_name, role, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
            (new.username, new.display_name, new.role, hash_password(new.password), now()))
        db.commit()
        return {"user": public_user(db.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone())}


def _active_admins(db, excluding: int) -> int:
    return db.execute("SELECT COUNT(*) FROM users WHERE role = 'admin' AND active = 1 AND id != ?",
                      (excluding,)).fetchone()[0]


@users_router.patch("/{user_id}")
def update_user(user_id: int, update: UserUpdate, _: AdminUser, config: Config) -> dict:
    with closing(auth_connect(config)) as db:
        row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="User not found.")
        demoting = (update.role is not None and update.role != "admin") or update.active is False
        if row["role"] == "admin" and row["active"] and demoting and _active_admins(db, user_id) == 0:
            raise HTTPException(status_code=400, detail="Keep at least one active administrator.")
        changes = {k: v for k, v in update.model_dump().items() if v is not None}
        if changes:
            db.execute(f"UPDATE users SET {', '.join(f'{k} = ?' for k in changes)} WHERE id = ?",
                       (*[int(v) if isinstance(v, bool) else v for v in changes.values()], user_id))
            if update.active is False or update.role is not None:
                db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            db.commit()
        return {"user": public_user(db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())}


@users_router.post("/{user_id}/password")
def reset_password(user_id: int, reset: PasswordReset, _: AdminUser, config: Config) -> dict:
    with closing(auth_connect(config)) as db:
        if db.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is None:
            raise HTTPException(status_code=404, detail="User not found.")
        db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(reset.new_password), user_id))
        db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        db.commit()
    return {"ok": True}
