from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth.dependencies import Identity
from auth.security import hash_secret
from models.join_request import JoinRequest
from models.pg_group import PGGroup
from models.user import User

_ALREADY_PENDING_MESSAGE = (
    "You already have a pending join request. Wait for it to be approved or "
    "rejected before requesting another PG."
)


def submit_join_request(db: Session, identity: Identity, access_key: str) -> JoinRequest:
    if identity.group_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "You already belong to a PG group")

    # A user may have at most one pending request across ALL groups, not just
    # the one being requested here — otherwise a user can accumulate pending
    # requests to several PGs and end up silently moved between them
    # depending on which owner happens to approve last (see decide_request's
    # matching guard below). This single check subsumes the old same-group
    # duplicate check.
    existing_pending = (
        db.query(JoinRequest)
        .filter(JoinRequest.user_id == identity.ref_id, JoinRequest.status == "pending")
        .first()
    )
    if existing_pending:
        raise HTTPException(status.HTTP_409_CONFLICT, _ALREADY_PENDING_MESSAGE)

    key_hash = hash_secret(access_key)
    group = db.query(PGGroup).filter(PGGroup.access_key_hash == key_hash).first()
    if not group:
        # Same error for "wrong key" as any other failure — do not reveal
        # whether a key was close to valid.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invalid access key")

    join_request = JoinRequest(user_id=identity.ref_id, group_id=group.group_id)
    db.add(join_request)
    try:
        db.commit()
    except IntegrityError:
        # Backstop for a genuine concurrent race: two submissions could both
        # pass the check above before either commits. The partial unique
        # index (uq_one_pending_request_per_user) catches that here.
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, _ALREADY_PENDING_MESSAGE)
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

    user = db.get(User, join_request.user_id) if approve else None
    if approve and user.group_id is not None:
        # The user was approved into a different PG (or, in principle, this
        # same one) after this request was submitted but before it was
        # decided. Approving would silently overwrite their existing
        # membership. Leave this request pending — untouched — so the owner
        # can see it and explicitly reject it with full context, rather than
        # having it auto-resolve in a way they never notice.
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This user already belongs to a PG group and cannot be approved into another.",
        )

    join_request.status = "approved" if approve else "rejected"
    join_request.decided_at = datetime.now(timezone.utc)

    if approve:
        user.group_id = identity.group_id
        user.joined_date = datetime.now(timezone.utc)

    db.commit()
    db.refresh(join_request)
    return join_request
