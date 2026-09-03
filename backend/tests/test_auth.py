import pytest

from rate_limit import limiter
from tests.conftest import register_owner, register_user, unique_email


def test_register_and_me_owner(client):
    register_owner(client, "Alice", "ABC PG")
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "owner"
    assert body["group_id"] is not None  # owners always have a group


def test_register_and_me_user_no_group_yet(client):
    register_user(client, "Charlie")
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "user"
    assert body["group_id"] is None  # not approved into any PG yet


def test_duplicate_email_rejected(client):
    email = unique_email("dup")
    payload = {"name": "X", "email": email, "password": "password123", "pg_name": "X PG"}
    r1 = client.post("/api/auth/register/owner", json=payload)
    assert r1.status_code == 201
    r2 = client.post("/api/auth/register/owner", json=payload)
    assert r2.status_code == 409


def test_login_wrong_password_rejected(client):
    email = unique_email("wp")
    client.post(
        "/api/auth/register/owner",
        json={"name": "X", "email": email, "password": "password123", "pg_name": "X PG"},
    )
    client.post("/api/auth/logout")
    resp = client.post("/api/auth/login", json={"email": email, "password": "wrong-password"})
    assert resp.status_code == 401


def test_unauthenticated_request_rejected(client):
    resp = client.get("/api/announcements")
    assert resp.status_code == 401


def test_logout_clears_session(client):
    register_owner(client, "Owner", "Some PG")
    assert client.get("/api/auth/me").status_code == 200
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401


def test_login_is_rate_limited(client):
    """Rate limiting is disabled under the test environment by default (see
    rate_limit.py) so unrelated tests don't trip shared in-memory limits.
    This test re-enables it just long enough to verify the wiring actually
    rejects excess requests, then restores the disabled state."""
    email = unique_email("ratelimited")
    limiter.enabled = True
    try:
        statuses = [
            client.post("/api/auth/login", json={"email": email, "password": "wrong"}).status_code
            for _ in range(15)
        ]
    finally:
        limiter.enabled = False
    assert 429 in statuses
