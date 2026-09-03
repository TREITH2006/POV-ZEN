from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from auth.dependencies import Identity
from auth.security import hash_secret
from models.join_request import JoinRequest
from models.pg_group import PGGroup
from models.user import User


def submit_join_request(db: Session, identity: Identity, access_key: str) -> JoinRequest:
    if identity.group_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "You already belong to a PG group")

    key_hash = hash_secret(access_key)
    group = db.query(PGGroup).filter(PGGroup.access_key_hash == key_hash).first()
    if not group:
        # Same error for "wrong key" as any other failure — do not reveal
        # whether a key was close to valid.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invalid access key")

    existing_pending = (
        db.query(JoinRequest)
        .filter(
            JoinRequest.user_id == identity.ref_id,
            JoinRequest.group_id == group.group_id,
            JoinRequest.status == "pending",
        )
        .first()
    )
    if existing_pending:
        raise HTTPException(status.HTTP_409_CONFLICT, "A pending request for this PG already exists")

    join_request = JoinRequest(user_id=identity.ref_id, group_id=group.group_id)
    db.add(join_request)
    db.commit()
    db.refresh(join_request)
    return join_request


def get_latest_request_for_user(db: Session, identity: Identity) -> JoinRequest | None:
    return (
        db.query(JoinRequest)
        .filter(JoinRequest.user_id == identity.ref_id)
        .order_by(JoinRequest.requested_at.desc())
        .first()
    )


def list_requests_for_owner(db: Session, identity: Identity) -> list[JoinRequest]:
    return (
        db.query(JoinRequest)
        .filter(JoinRequest.group_id == identity.group_id, JoinRequest.status == "pending")
        .order_by(JoinRequest.requested_at.asc())
        .all()
    )


def decide_request(db: Session, identity: Identity, request_id: str, approve: bool) -> JoinRequest:
    join_request = (
        db.query(JoinRequest)
        .filter(JoinRequest.request_id == request_id, JoinRequest.group_id == identity.group_id)
        .first()
    )
    if not join_request:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Join request not found")
    if join_request.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, "Request has already been decided")

    join_request.status = "approved" if approve else "rejected"
    join_request.decided_at = datetime.now(timezone.utc)

    if approve:
        user = db.get(User, join_request.user_id)
        user.group_id = identity.group_id
        user.joined_date = datetime.now(timezone.utc)

    db.commit()
    db.refresh(join_request)
    return join_request
