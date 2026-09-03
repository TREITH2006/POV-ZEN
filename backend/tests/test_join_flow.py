import pytest
from sqlalchemy.exc import IntegrityError

from models.join_request import JoinRequest
from tests.conftest import register_owner, register_user


def test_join_request_lifecycle(make_client):
    owner = make_client()
    user = make_client()

    group = register_owner(owner, "Owner", "Test PG")
    register_user(user, "Newbie")

    resp = user.post("/api/join-requests", json={"access_key": group["access_key"]})
    assert resp.status_code == 201
    assert resp.json()["status"] == "pending"

    # Not yet approved: cannot see group-scoped data.
    assert user.get("/api/announcements").status_code == 403

    pending = owner.get("/api/join-requests").json()
    assert len(pending) == 1
    request_id = pending[0]["request_id"]

    decided = owner.patch(f"/api/join-requests/{request_id}/decision", json={"approve": True})
    assert decided.status_code == 200
    assert decided.json()["status"] == "approved"

    # Now approved: can see (empty) group-scoped data.
    assert user.get("/api/announcements").status_code == 200


def test_invalid_access_key_rejected(make_client):
    user = make_client()
    register_user(user, "Someone")
    resp = user.post("/api/join-requests", json={"access_key": "TOTALLY-WRONG-KEY"})
    assert resp.status_code == 404


def test_duplicate_pending_request_rejected(make_client):
    owner = make_client()
    user = make_client()
    group = register_owner(owner, "Owner", "Test PG")
    register_user(user, "Newbie")

    first = user.post("/api/join-requests", json={"access_key": group["access_key"]})
    assert first.status_code == 201
    second = user.post("/api/join-requests", json={"access_key": group["access_key"]})
    assert second.status_code == 409


def test_rejected_request_can_be_retried(make_client):
    owner = make_client()
    user = make_client()
    group = register_owner(owner, "Owner", "Test PG")
    register_user(user, "Newbie")

    resp = user.post("/api/join-requests", json={"access_key": group["access_key"]})
    request_id = resp.json()["request_id"]
    owner.patch(f"/api/join-requests/{request_id}/decision", json={"approve": False})

    retry = user.post("/api/join-requests", json={"access_key": group["access_key"]})
    assert retry.status_code == 201


def test_user_can_check_own_latest_request(make_client):
    owner = make_client()
    user = make_client()
    group = register_owner(owner, "Owner", "Test PG")
    register_user(user, "Newbie")

    assert user.get("/api/join-requests/mine").json() is None

    user.post("/api/join-requests", json={"access_key": group["access_key"]})
    mine = user.get("/api/join-requests/mine").json()
    assert mine["status"] == "pending"


def test_only_owner_can_decide_requests(make_client):
    owner = make_client()
    user = make_client()
    group = register_owner(owner, "Owner", "Test PG")
    register_user(user, "Newbie")

    resp = user.post("/api/join-requests", json={"access_key": group["access_key"]})
    request_id = resp.json()["request_id"]

    forbidden = user.patch(f"/api/join-requests/{request_id}/decision", json={"approve": True})
    assert forbidden.status_code == 403


# --- Multi-PG join protection -------------------------------------------------
# A user must never be able to hold more than one pending request, and must
# never be silently moved from one PG to another via a stale pending request
# that gets approved after the user is already a member elsewhere.


def test_cannot_submit_second_pending_request_to_different_group(make_client):
    owner_a = make_client()
    owner_b = make_client()
    user = make_client()

    group_a = register_owner(owner_a, "OwnerA", "PG A")
    group_b = register_owner(owner_b, "OwnerB", "PG B")
    register_user(user, "Newbie")

    first = user.post("/api/join-requests", json={"access_key": group_a["access_key"]})
    assert first.status_code == 201

    # PG-A's request is still pending — requesting PG-B must be rejected,
    # not just requesting PG-A again.
    second = user.post("/api/join-requests", json={"access_key": group_b["access_key"]})
    assert second.status_code == 409


def test_approving_request_cannot_overwrite_existing_membership(make_client):
    """Approval-time guard, isolated from the submission-time guard and the
    DB partial index: even if a pending request exists for a user who is
    already an approved member elsewhere — a state the normal API can no
    longer produce, but which a stray/direct insert could — approving it
    must not silently overwrite their existing group_id.

    (The submission-time check plus the partial unique index already make
    the original "two simultaneous pending requests" scenario unreachable
    through the API; this test exercises decide_request's own independent
    guard directly, which is what actually prevents the group_id
    overwrite regardless of how a stray pending request came to exist.)"""
    owner_a = make_client()
    owner_b = make_client()
    user = make_client()

    group_a = register_owner(owner_a, "OwnerA", "PG A")
    group_b = register_owner(owner_b, "OwnerB", "PG B")
    register_user(user, "Newbie")

    from tests.conftest import join_and_approve

    join_and_approve(owner_a, user, group_a["access_key"])  # user is now a PG-A member
    user_id = user.get("/api/auth/me").json()["ref_id"]

    # The request_a row is now "approved", so no pending row exists for this
    # user — inserting a stray pending request for PG-B does not violate the
    # partial unique index. This reproduces the state the approval-time
    # guard defends against, without needing two simultaneously-pending rows.
    from database import SessionLocal

    db = SessionLocal()
    try:
        stray_request = JoinRequest(user_id=user_id, group_id=group_b["group_id"])
        db.add(stray_request)
        db.commit()
        db.refresh(stray_request)
        stray_request_id = stray_request.request_id
    finally:
        db.close()

    approve_b = owner_b.patch(f"/api/join-requests/{stray_request_id}/decision", json={"approve": True})
    assert approve_b.status_code == 409

    me = user.get("/api/auth/me").json()
    assert me["group_id"] == group_a["group_id"]

    # PG-B's request must remain untouched (still pending) so its owner sees
    # it and can explicitly reject it with full context.
    pending_b = owner_b.get("/api/join-requests").json()
    assert any(r["request_id"] == stray_request_id and r["status"] == "pending" for r in pending_b)


def test_partial_unique_index_blocks_concurrent_duplicate_pending_requests(make_client):
    """Bypasses the service-layer check entirely to prove the DB-level
    partial unique index itself enforces the constraint, independent of
    application logic (the race-condition backstop)."""
    owner = make_client()
    user = make_client()
    group = register_owner(owner, "Owner", "Test PG")
    register_user(user, "Newbie")
    user_id = user.get("/api/auth/me").json()["ref_id"]

    from database import SessionLocal

    db = SessionLocal()
    try:
        db.add(JoinRequest(user_id=user_id, group_id=group["group_id"]))
        db.commit()

        db.add(JoinRequest(user_id=user_id, group_id=group["group_id"]))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        db.close()


def test_rejected_request_does_not_block_new_pending_request(make_client):
    """Regression: the global pending-check must be scoped to status
    'pending' only — a rejected request must not block joining elsewhere."""
    owner_a = make_client()
    owner_b = make_client()
    user = make_client()

    group_a = register_owner(owner_a, "OwnerA", "PG A")
    group_b = register_owner(owner_b, "OwnerB", "PG B")
    register_user(user, "Newbie")

    resp = user.post("/api/join-requests", json={"access_key": group_a["access_key"]})
    request_id = resp.json()["request_id"]
    owner_a.patch(f"/api/join-requests/{request_id}/decision", json={"approve": False})

    retry = user.post("/api/join-requests", json={"access_key": group_b["access_key"]})
    assert retry.status_code == 201


def test_approved_member_still_blocked_from_new_join_request(make_client):
    """Regression: an already-approved member must still be blocked from
    submitting a new join request (pre-existing behavior, must not regress)."""
    owner_a = make_client()
    owner_b = make_client()
    user = make_client()

    group_a = register_owner(owner_a, "OwnerA", "PG A")
    group_b = register_owner(owner_b, "OwnerB", "PG B")
    register_user(user, "Newbie")

    from tests.conftest import join_and_approve

    join_and_approve(owner_a, user, group_a["access_key"])

    resp = user.post("/api/join-requests", json={"access_key": group_b["access_key"]})
    assert resp.status_code == 409
