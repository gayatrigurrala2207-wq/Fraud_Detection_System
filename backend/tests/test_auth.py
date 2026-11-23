"""Authentication: first-run setup, sign-in, sessions, roles, and admin safeguards."""

from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient
import pytest

from app.auth import SESSION_COOKIE, _failures, hash_password, verify_password
from app.config import Settings, get_settings
from app.main import app

ADMIN = {"username": "admin.user", "display_name": "Admin User", "password": "correct-horse-1"}


@pytest.fixture
def client():
    with TemporaryDirectory() as directory:
        app.dependency_overrides[get_settings] = lambda: Settings("test", Path(directory), ())
        _failures.clear()
        yield TestClient(app)
        app.dependency_overrides.clear()


def test_password_hash_round_trip_and_salting():
    first, second = hash_password("s3cret-password"), hash_password("s3cret-password")
    assert first != second and first.startswith("scrypt$")
    assert verify_password("s3cret-password", first)
    assert not verify_password("wrong-password", first)
    assert not verify_password("anything", "not-a-hash")


def test_everything_requires_sign_in_except_auth_status(client):
    for path in ("/api/overview", "/api/health", "/api/transactions", "/api/settings", "/api/users"):
        assert client.get(path).status_code == 401, path
    assert client.get("/api/auth/status").json()["setup_required"] is True


def test_first_run_setup_creates_admin_once(client):
    response = client.post("/api/auth/setup", json=ADMIN)
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "admin"
    cookie = response.headers["set-cookie"].lower()
    assert SESSION_COOKIE in cookie and "httponly" in cookie and "samesite=lax" in cookie
    assert client.get("/api/auth/me").json()["user"]["username"] == "admin.user"
    assert client.post("/api/auth/setup", json={**ADMIN, "username": "second"}).status_code == 409


def test_short_password_rejected(client):
    assert client.post("/api/auth/setup", json={**ADMIN, "password": "short"}).status_code == 422


def test_login_logout_and_rate_limit(client):
    client.post("/api/auth/setup", json=ADMIN)
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401

    assert client.post("/api/auth/login", json={"username": "admin.user", "password": "nope"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "ADMIN.USER", "password": ADMIN["password"]}).status_code == 200
    assert client.get("/api/auth/me").status_code == 200

    client.post("/api/auth/logout")
    for _ in range(5):
        client.post("/api/auth/login", json={"username": "admin.user", "password": "wrong"})
    assert client.post("/api/auth/login", json={"username": "admin.user", "password": ADMIN["password"]}).status_code == 429


def test_roles_and_user_management(client):
    client.post("/api/auth/setup", json=ADMIN)
    created = client.post("/api/users", json={"username": "viewer1", "display_name": "View Only",
                                              "password": "viewer-password", "role": "viewer"})
    assert created.status_code == 201
    viewer_id = created.json()["user"]["id"]
    assert client.post("/api/users", json={"username": "viewer1", "display_name": "x",
                                           "password": "viewer-password"}).status_code == 409

    # The only admin cannot be demoted or disabled.
    admin_id = client.get("/api/auth/me").json()["user"]["id"]
    assert client.patch(f"/api/users/{admin_id}", json={"role": "analyst"}).status_code == 400
    assert client.patch(f"/api/users/{admin_id}", json={"active": False}).status_code == 400

    viewer = TestClient(app)
    assert viewer.post("/api/auth/login", json={"username": "viewer1", "password": "viewer-password"}).status_code == 200
    assert viewer.get("/api/users").status_code == 403
    assert viewer.post("/api/replay", json={"action": "pause"}).status_code == 403
    assert viewer.post("/api/cases/1/label", json={"disposition": "fraud"}).status_code == 403

    # Disabling an account ends its sessions immediately.
    assert client.patch(f"/api/users/{viewer_id}", json={"active": False}).json()["user"]["active"] is False
    assert viewer.get("/api/auth/me").status_code == 401


def test_change_password_requires_current(client):
    client.post("/api/auth/setup", json=ADMIN)
    bad = {"current_password": "wrong", "new_password": "another-password-2"}
    assert client.post("/api/auth/password", json=bad).status_code == 400
    good = {"current_password": ADMIN["password"], "new_password": "another-password-2"}
    assert client.post("/api/auth/password", json=good).status_code == 200
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json={"username": "admin.user", "password": "another-password-2"}).status_code == 200
