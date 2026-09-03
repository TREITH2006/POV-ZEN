"""Food feedback: one record per resident per menu, future-date rejection,
update-not-duplicate semantics, and group isolation.
"""

from datetime import date, timedelta

import pytest
import sqlalchemy as sa

from database import SessionLocal
from models.food_feedback import FoodFeedback
from tests.conftest import join_and_approve, register_owner, register_user

PAST_DATE = "2020-01-01"
FUTURE_DATE = "2099-01-01"


def _create_menu(owner_client, menu_date: str, lunch: str = "Rice") -> dict:
    resp = owner_client.post("/api/food", json={"menu_date": menu_date, "lunch": lunch})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _setup_owner_and_approved_user(make_client):
    owner = make_client()
    user = make_client()
    group = register_owner(owner, "FeedbackOwner", "Feedback PG")
    register_user(user, "FeedbackUser")
    join_and_approve(owner, user, group["access_key"])
    return owner, user, group


def test_duplicate_feedback_updates_existing_record_not_duplicates(make_client):
    owner, user, _ = _setup_owner_and_approved_user(make_client)
    menu = _create_menu(owner, PAST_DATE)

    first = user.post(f"/api/food/{menu['id']}/feedback", json={"rating": "good", "comment": "Nice"})
    assert first.status_code == 201
    first_id = first.json()["id"]

    second = user.post(f"/api/food/{menu['id']}/feedback", json={"rating": "bad", "comment": "Changed my mind"})
    assert second.status_code == 201
    assert second.json()["id"] == first_id  # same row, updated in place
    assert second.json()["rating"] == "bad"
    assert second.json()["comment"] == "Changed my mind"

    all_feedback = owner.get(f"/api/food/{menu['id']}/feedback").json()
    assert len(all_feedback) == 1


def test_feedback_rejected_for_future_dated_menu(make_client):
    owner, user, _ = _setup_owner_and_approved_user(make_client)
    menu = _create_menu(owner, FUTURE_DATE)

    resp = user.post(f"/api/food/{menu['id']}/feedback", json={"rating": "good"})
    assert resp.status_code == 422


def test_feedback_allowed_for_todays_menu(make_client):
    owner, user, _ = _setup_owner_and_approved_user(make_client)
    menu = _create_menu(owner, date.today().isoformat())

    resp = user.post(f"/api/food/{menu['id']}/feedback", json={"rating": "average"})
    assert resp.status_code == 201


def test_feedback_allowed_for_past_menu(make_client):
    owner, user, _ = _setup_owner_and_approved_user(make_client)
    menu = _create_menu(owner, PAST_DATE)

    resp = user.post(f"/api/food/{menu['id']}/feedback", json={"rating": "good"})
    assert resp.status_code == 201


def test_database_unique_constraint_blocks_direct_duplicate_insert(make_client):
    """Proves the DB constraint itself, bypassing the service-layer upsert."""
    owner, user, group = _setup_owner_and_approved_user(make_client)
    menu = _create_menu(owner, PAST_DATE)
    user_id = user.get("/api/auth/me").json()["ref_id"]

    db = SessionLocal()
    try:
        db.add(FoodFeedback(menu_id=menu["id"], user_id=user_id, group_id=group["group_id"], rating="good"))
        db.commit()

        db.add(FoodFeedback(menu_id=menu["id"], user_id=user_id, group_id=group["group_id"], rating="bad"))
        with pytest.raises(sa.exc.IntegrityError):
            db.commit()
        db.rollback()
    finally:
        db.close()


def test_unapproved_user_cannot_submit_feedback(make_client):
    owner, _, _ = _setup_owner_and_approved_user(make_client)
    menu = _create_menu(owner, PAST_DATE)

    pending_user = make_client()
    register_user(pending_user, "PendingFeedbackUser")
    resp = pending_user.post(f"/api/food/{menu['id']}/feedback", json={"rating": "good"})
    assert resp.status_code == 403


def test_cross_group_user_cannot_submit_feedback_on_other_groups_menu(two_groups):
    owner_a = two_groups["owner_a"]
    user_b = two_groups["user_b"]

    menu = _create_menu(owner_a, PAST_DATE)
    resp = user_b.post(f"/api/food/{menu['id']}/feedback", json={"rating": "good"})
    assert resp.status_code == 404  # menu not found in user_b's own group


def test_cross_group_owner_cannot_list_other_groups_feedback(two_groups):
    owner_a = two_groups["owner_a"]
    owner_b = two_groups["owner_b"]
    user_a = two_groups["user_a"]

    menu = _create_menu(owner_a, PAST_DATE)
    user_a.post(f"/api/food/{menu['id']}/feedback", json={"rating": "good"})

    resp = owner_b.get(f"/api/food/{menu['id']}/feedback")
    assert resp.status_code == 404


def test_feedback_response_includes_updated_at(make_client):
    owner, user, _ = _setup_owner_and_approved_user(make_client)
    menu = _create_menu(owner, PAST_DATE)

    resp = user.post(f"/api/food/{menu['id']}/feedback", json={"rating": "good"})
    assert resp.status_code == 201
    assert "updated_at" in resp.json()
