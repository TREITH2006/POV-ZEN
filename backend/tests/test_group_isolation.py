"""Mandatory cross-group isolation tests (spec section: PG group isolation).

Every one of these must DENY. If any starts passing data across groups, that
is a critical security regression.
"""


def test_announcement_isolation(two_groups):
    owner_a = two_groups["owner_a"]
    user_b = two_groups["user_b"]

    owner_a.post("/api/announcements", json={"title": "A only", "message": "secret to group A"})

    resp = user_b.get("/api/announcements")
    assert resp.status_code == 200
    assert resp.json() == []  # PG002 user must never see PG001's announcement


def test_owner_cannot_decide_other_groups_join_request(two_groups, make_client):
    owner_b = two_groups["owner_b"]
    group_a = two_groups["group_a"]
    user_c = make_client()

    from tests.conftest import register_user

    register_user(user_c, "Eve")
    resp = user_c.post("/api/join-requests", json={"access_key": group_a["access_key"]})
    request_id = resp.json()["request_id"]

    # Owner B must not be able to approve/reject a request belonging to group A.
    forbidden = owner_b.patch(f"/api/join-requests/{request_id}/decision", json={"approve": True})
    assert forbidden.status_code == 404


def test_food_menu_isolation(two_groups):
    owner_a = two_groups["owner_a"]
    user_b = two_groups["user_b"]

    owner_a.post("/api/food", json={"menu_date": "2026-09-03", "lunch": "Rice"})

    resp = user_b.get("/api/food/today")
    assert resp.status_code == 200
    assert resp.json() is None  # group B has no menu for today


def test_rent_isolation_owner_cannot_target_other_groups_user(two_groups):
    owner_b = two_groups["owner_b"]
    user_a_me = two_groups["user_a"].get("/api/auth/me").json()

    resp = owner_b.post(
        "/api/rent",
        json={"user_id": user_a_me["ref_id"], "monthly_rent": 5000, "due_date": "2026-09-10"},
    )
    assert resp.status_code == 404  # user does not belong to Owner B's group


def test_document_isolation(two_groups):
    owner_a = two_groups["owner_a"]
    user_b = two_groups["user_b"]

    owner_a.post(
        "/api/documents",
        data={"title": "Rules", "category": "rules"},
        files={"file": ("rules.pdf", b"%PDF-1.4\n%fake", "application/pdf")},
    )

    resp = user_b.get("/api/documents")
    assert resp.status_code == 200
    assert resp.json() == []


def test_owner_contact_scoped_to_own_group(two_groups):
    user_a = two_groups["user_a"]
    user_b = two_groups["user_b"]

    contact_a = user_a.get("/api/groups/owner-contact").json()
    contact_b = user_b.get("/api/groups/owner-contact").json()

    assert contact_a["name"] == "Alice"
    assert contact_b["name"] == "Bob"
    assert contact_a["name"] != contact_b["name"]


def test_group_user_listing_scoped(two_groups):
    owner_a = two_groups["owner_a"]
    users = owner_a.get("/api/groups/users").json()
    names = {u["name"] for u in users}
    assert names == {"Charlie"}  # not Dana, who is in group B
