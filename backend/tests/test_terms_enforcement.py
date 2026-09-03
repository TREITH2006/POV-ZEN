"""Backend enforcement of Terms & Conditions acceptance.

Before this fix, only /api/terms/* itself checked acceptance — every other
protected route (announcements, food, issues, rent, documents, groups,
join-requests) was reachable by any authenticated user regardless of Terms
status. The frontend's terms.html redirect was the only gate, which is not
a security boundary (any direct API call, e.g. via curl, bypassed it
entirely). /api/announcements is used here as the representative protected
endpoint — it's gated by require_group_member, which every fixed dependency
(require_owner, require_user, require_group_member) now routes through.

Note: register_owner/register_user (tests/conftest.py) accept the current
Terms version by default, since nearly every other test in this suite
relies on that setup working without itself worrying about Terms. The tests
below that need the NOT-yet-accepted state pass accept_terms=False.
"""

import pytest
import sqlalchemy as sa

from database import SessionLocal
from models.terms_acceptance import TermsAcceptance
from tests.conftest import register_owner


def test_authenticated_without_terms_acceptance_is_blocked(client):
    register_owner(client, "NoTermsOwner", "No Terms PG", accept_terms=False)
    resp = client.get("/api/announcements")
    assert resp.status_code == 403


def test_authenticated_with_terms_acceptance_is_allowed(client):
    register_owner(client, "CompliantOwner", "Compliant PG")  # accepts by default
    resp = client.get("/api/announcements")
    assert resp.status_code == 200


def test_unauthenticated_user_gets_401_not_403(client):
    """The terms check must not run before authentication — an
    unauthenticated request should fail on "not logged in", not be
    misreported as a terms problem."""
    resp = client.get("/api/announcements")
    assert resp.status_code == 401


def test_terms_and_me_endpoints_remain_reachable_without_acceptance(client):
    """/api/auth/me and /api/terms/* must stay reachable pre-acceptance —
    otherwise a user could never discover they need to accept, or ever
    accept at all."""
    register_owner(client, "BootstrapOwner", "Bootstrap PG", accept_terms=False)

    me = client.get("/api/auth/me")
    assert me.status_code == 200

    status_resp = client.get("/api/terms/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["accepted"] is False

    accept = client.post("/api/terms/accept", json={})
    assert accept.status_code == 200


def test_version_bump_requires_re_acceptance(client, monkeypatch):
    register_owner(client, "VersionedOwner", "Versioned PG")  # accepts current version ("1.0") by default
    assert client.get("/api/announcements").status_code == 200

    # Simulate a Terms version bump.
    monkeypatch.setattr("auth.dependencies.CURRENT_TERMS_VERSION", "2.0")

    # The old acceptance record (version "1.0") no longer satisfies the
    # current version — access must be blocked again.
    assert client.get("/api/announcements").status_code == 403

    # /api/terms/status must also reflect the bump (also reads the constant).
    monkeypatch.setattr("routes.terms.CURRENT_TERMS_VERSION", "2.0")
    status_resp = client.get("/api/terms/status")
    assert status_resp.json() == {"accepted": False, "version": "2.0"}

    # Re-accepting the new version explicitly restores access.
    accept = client.post("/api/terms/accept", json={"version": "2.0"})
    assert accept.status_code == 200
    assert client.get("/api/announcements").status_code == 200


def test_role_and_membership_checks_still_apply_after_terms_check(client):
    """Regression: the terms gate must not short-circuit or replace the
    existing role/ownership checks it now sits in front of."""
    register_owner(client, "RoleCheckOwner", "RoleCheck PG")  # accepts by default

    # An Owner (not a User) hitting a user-only-shaped flow should still get
    # the pre-existing role error, not a terms error, once terms are accepted.
    # Checking the message, not just the status code, since both errors are
    # 403 — this proves it's the role check firing, not a stale terms block.
    resp = client.post("/api/join-requests", json={"access_key": "whatever"})
    assert resp.status_code == 403
    assert resp.json()["detail"] == "User access required"


# --- Uniqueness and idempotency -----------------------------------------------


def test_repeated_accept_does_not_create_duplicate_rows(client):
    register_owner(client, "RepeatAccept", "Repeat PG")  # already accepted once by the helper

    for _ in range(3):
        resp = client.post("/api/terms/accept", json={})
        assert resp.status_code == 200

    me = client.get("/api/auth/me").json()
    db = SessionLocal()
    try:
        count = (
            db.query(TermsAcceptance)
            .filter(TermsAcceptance.account_id == me["account_id"], TermsAcceptance.version == "1.0")
            .count()
        )
    finally:
        db.close()
    assert count == 1


def test_accepting_different_versions_creates_separate_rows(client, monkeypatch):
    register_owner(client, "MultiVersion", "MultiVersion PG")  # accepts "1.0" by default
    assert client.post("/api/terms/accept", json={"version": "2.0"}).status_code == 200

    me = client.get("/api/auth/me").json()
    db = SessionLocal()
    try:
        versions = {
            row.version
            for row in db.query(TermsAcceptance).filter(TermsAcceptance.account_id == me["account_id"]).all()
        }
    finally:
        db.close()
    assert versions == {"1.0", "2.0"}


def test_database_unique_constraint_rejects_direct_duplicate_insert(client):
    """Proves the constraint itself, not just the service-layer check —
    bypasses accept_terms() entirely."""
    register_owner(client, "DirectInsert", "Direct PG")
    me = client.get("/api/auth/me").json()

    db = SessionLocal()
    try:
        db.add(TermsAcceptance(account_id=me["account_id"], version="1.0"))
        with pytest.raises(sa.exc.IntegrityError):
            db.commit()
        db.rollback()
    finally:
        db.close()
