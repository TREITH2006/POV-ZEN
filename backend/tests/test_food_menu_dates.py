"""Date-specific food menu management.

Before this fix, the only way to retrieve a menu via the API was
GET /api/food/today (hardcoded to date.today()) — there was no way to view,
and therefore no safe way to edit, a menu for any other date. This exercises
the new GET /api/food/by-date/{menu_date} route alongside the existing
create/update endpoints, using a fixed non-today date throughout so these
tests don't depend on when they happen to run.
"""

from tests.conftest import register_owner, register_user

FUTURE_DATE = "2030-01-15"
OTHER_DATE = "2030-01-16"


def test_create_menu_for_specific_date(client):
    register_owner(client, "MenuOwner", "Menu PG")

    resp = client.post(
        "/api/food",
        json={"menu_date": FUTURE_DATE, "breakfast": "Poha", "lunch": "Dal Rice", "dinner": "Khichdi"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["menu_date"] == FUTURE_DATE
    assert body["breakfast"] == "Poha"


def test_retrieve_menu_by_date(client):
    register_owner(client, "MenuOwner", "Menu PG")
    client.post("/api/food", json={"menu_date": FUTURE_DATE, "lunch": "Dal Rice"})

    resp = client.get(f"/api/food/by-date/{FUTURE_DATE}")
    assert resp.status_code == 200
    assert resp.json()["lunch"] == "Dal Rice"


def test_retrieve_by_date_returns_null_when_no_menu_exists(client):
    register_owner(client, "MenuOwner", "Menu PG")
    resp = client.get(f"/api/food/by-date/{FUTURE_DATE}")
    assert resp.status_code == 200
    assert resp.json() is None


def test_by_date_does_not_leak_a_different_dates_menu(client):
    """A menu created for one date must not appear when querying another."""
    register_owner(client, "MenuOwner", "Menu PG")
    client.post("/api/food", json={"menu_date": FUTURE_DATE, "lunch": "Dal Rice"})

    resp = client.get(f"/api/food/by-date/{OTHER_DATE}")
    assert resp.status_code == 200
    assert resp.json() is None


def test_update_existing_menu_for_date_via_upsert(client):
    """Posting again for the same date updates it in place rather than
    creating a duplicate (existing upsert behavior, now reachable end-to-end
    via the new retrieval route)."""
    register_owner(client, "MenuOwner", "Menu PG")

    first = client.post(
        "/api/food", json={"menu_date": FUTURE_DATE, "breakfast": "Poha", "lunch": "Dal Rice", "dinner": "Roti"}
    )
    menu_id = first.json()["id"]

    second = client.post(
        "/api/food", json={"menu_date": FUTURE_DATE, "breakfast": "Idli", "lunch": "Dal Rice", "dinner": "Roti"}
    )
    assert second.status_code == 201
    assert second.json()["id"] == menu_id  # same row, not a new one

    fetched = client.get(f"/api/food/by-date/{FUTURE_DATE}").json()
    assert fetched["breakfast"] == "Idli"
    assert fetched["lunch"] == "Dal Rice"


def test_update_menu_by_id_still_works(client):
    """Regression: the existing PUT /api/food/{menu_id} partial-update path
    must be unaffected by the new retrieval route."""
    register_owner(client, "MenuOwner", "Menu PG")
    created = client.post("/api/food", json={"menu_date": FUTURE_DATE, "dinner": "Roti"}).json()

    updated = client.put(f"/api/food/{created['id']}", json={"dinner": "Paratha"})
    assert updated.status_code == 200
    assert updated.json()["dinner"] == "Paratha"

    fetched = client.get(f"/api/food/by-date/{FUTURE_DATE}").json()
    assert fetched["dinner"] == "Paratha"


def test_by_date_group_isolation(two_groups):
    """The new route must enforce the same group_id isolation as every
    other menu endpoint — a menu created in one PG must be invisible to
    the other, for an explicit non-today date."""
    owner_a = two_groups["owner_a"]
    user_b = two_groups["user_b"]

    owner_a.post("/api/food", json={"menu_date": FUTURE_DATE, "lunch": "Group A Special"})

    resp = user_b.get(f"/api/food/by-date/{FUTURE_DATE}")
    assert resp.status_code == 200
    assert resp.json() is None  # group B must not see group A's menu


def test_by_date_visible_to_approved_user_in_same_group(two_groups):
    owner_a = two_groups["owner_a"]
    user_a = two_groups["user_a"]

    owner_a.post("/api/food", json={"menu_date": FUTURE_DATE, "lunch": "Shared Lunch"})

    resp = user_a.get(f"/api/food/by-date/{FUTURE_DATE}")
    assert resp.status_code == 200
    assert resp.json()["lunch"] == "Shared Lunch"


def test_by_date_requires_group_membership(client):
    """An authenticated user with no approved PG membership yet must still
    be blocked, same as /api/food/today already enforces."""
    register_user(client, "PendingUser")
    resp = client.get(f"/api/food/by-date/{FUTURE_DATE}")
    assert resp.status_code == 403


def test_by_date_rejects_malformed_date(client):
    register_owner(client, "MenuOwner", "Menu PG")
    resp = client.get("/api/food/by-date/not-a-date")
    assert resp.status_code == 422
