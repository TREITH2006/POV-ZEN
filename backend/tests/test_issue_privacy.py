from tests.conftest import join_and_approve, register_owner, register_user


def test_user_sees_only_own_issues(make_client):
    owner = make_client()
    user1 = make_client()
    user2 = make_client()

    group = register_owner(owner, "Owner", "Test PG")
    register_user(user1, "User1")
    register_user(user2, "User2")
    join_and_approve(owner, user1, group["access_key"])
    join_and_approve(owner, user2, group["access_key"])

    user1.post("/api/issues", data={"category": "plumbing", "description": "Leaking tap"})

    assert len(user1.get("/api/issues/mine").json()) == 1
    assert len(user2.get("/api/issues/mine").json()) == 0  # same PG, different user


def test_owner_sees_all_group_issues(make_client):
    owner = make_client()
    user1 = make_client()
    group = register_owner(owner, "Owner", "Test PG")
    register_user(user1, "User1")
    join_and_approve(owner, user1, group["access_key"])

    user1.post("/api/issues", data={"category": "wifi", "description": "No internet"})

    issues = owner.get("/api/issues").json()
    assert len(issues) == 1
    assert issues[0]["category"] == "wifi"


def test_user_cannot_list_group_issues(make_client):
    user1 = make_client()
    register_user(user1, "User1")
    resp = user1.get("/api/issues")
    assert resp.status_code == 403


def test_only_owner_can_update_issue_status(make_client):
    owner = make_client()
    user1 = make_client()
    group = register_owner(owner, "Owner", "Test PG")
    register_user(user1, "User1")
    join_and_approve(owner, user1, group["access_key"])

    created = user1.post("/api/issues", data={"category": "room", "description": "Broken door"}).json()

    forbidden = user1.patch(f"/api/issues/{created['id']}/status", json={"status": "resolved"})
    assert forbidden.status_code == 403

    allowed = owner.patch(f"/api/issues/{created['id']}/status", json={"status": "resolved"})
    assert allowed.status_code == 200
    assert allowed.json()["status"] == "resolved"


def test_unapproved_user_cannot_submit_issue(make_client):
    user = make_client()
    register_user(user, "Pending")
    resp = user.post("/api/issues", data={"category": "other", "description": "test"})
    assert resp.status_code == 403
