import os
import sys
import tempfile
import uuid

import pytest

# Environment must be set BEFORE any application module is imported, since
# config.get_settings() and several modules cache a Settings() instance at
# import time (module caching means later per-test env overrides would be
# silently ignored otherwise).
_TEST_DIR = tempfile.mkdtemp(prefix="pov_zen_test_")
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DIR}/test.db"
os.environ["UPLOAD_DIR"] = os.path.join(_TEST_DIR, "uploads")
os.environ["CORS_ORIGINS"] = "http://localhost:5500,http://127.0.0.1:5500"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

import models  # noqa: F401,E402
from database import Base, engine  # noqa: E402
from main import app  # noqa: E402

Base.metadata.create_all(bind=engine)


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def make_client():
    """Factory for extra TestClient instances with independent cookie jars,
    used to simulate multiple concurrently logged-in accounts in one test."""
    created = []

    def _make():
        c = TestClient(app)
        created.append(c)
        return c

    yield _make
    for c in created:
        c.close()


def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


def register_owner(c: TestClient, name: str, pg_name: str, accept_terms: bool = True) -> dict:
    resp = c.post(
        "/api/auth/register/owner",
        json={"name": name, "email": unique_email(name.lower()), "password": "password123", "pg_name": pg_name},
    )
    assert resp.status_code == 201, resp.text
    if accept_terms:
        accepted = c.post("/api/terms/accept", json={})
        assert accepted.status_code == 200, accepted.text
    return resp.json()


def register_user(c: TestClient, name: str, accept_terms: bool = True) -> dict:
    resp = c.post(
        "/api/auth/register/user",
        json={"name": name, "email": unique_email(name.lower()), "password": "password123"},
    )
    assert resp.status_code == 201, resp.text
    if accept_terms:
        accepted = c.post("/api/terms/accept", json={})
        assert accepted.status_code == 200, accepted.text
    return resp.json()


def join_and_approve(owner_client: TestClient, user_client: TestClient, access_key: str) -> None:
    resp = user_client.post("/api/join-requests", json={"access_key": access_key})
    assert resp.status_code == 201, resp.text
    request_id = resp.json()["request_id"]
    resp = owner_client.patch(f"/api/join-requests/{request_id}/decision", json={"approve": True})
    assert resp.status_code == 200, resp.text


@pytest.fixture()
def two_groups(make_client):
    """Two fully isolated PGs, each with an Owner and one approved User."""
    owner_a = make_client()
    owner_b = make_client()
    user_a = make_client()
    user_b = make_client()

    group_a = register_owner(owner_a, "Alice", "ABC PG")
    group_b = register_owner(owner_b, "Bob", "XYZ PG")

    register_user(user_a, "Charlie")
    register_user(user_b, "Dana")

    join_and_approve(owner_a, user_a, group_a["access_key"])
    join_and_approve(owner_b, user_b, group_b["access_key"])

    return {
        "owner_a": owner_a,
        "owner_b": owner_b,
        "user_a": user_a,
        "user_b": user_b,
        "group_a": group_a,
        "group_b": group_b,
    }
