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
