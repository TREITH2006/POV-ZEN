from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from auth.security import COOKIE_NAME, decode_access_token
from database import get_db
from models.owner import Owner
from models.user import User


@dataclass(frozen=True)
class Identity:
    account_id: str
    role: str  # "owner" | "user"
    ref_id: str  # owner_id | user_id
    group_id: str | None  # always freshly loaded from the DB, never from the token


def get_current_identity(request: Request, db: Session = Depends(get_db)) -> Identity:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")

    role = payload.get("role")
    ref_id = payload.get("ref_id")
    account_id = payload.get("sub")

    if role == "owner":
        owner = db.get(Owner, ref_id)
        if not owner or owner.account_id != account_id:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account no longer valid")
        group_id = owner.pg_group.group_id if owner.pg_group else None
        return Identity(account_id=account_id, role="owner", ref_id=owner.owner_id, group_id=group_id)

    if role == "user":
        user = db.get(User, ref_id)
        if not user or user.account_id != account_id:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account no longer valid")
        return Identity(account_id=account_id, role="user", ref_id=user.user_id, group_id=user.group_id)

    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid session role")


def require_owner(identity: Identity = Depends(get_current_identity)) -> Identity:
    if identity.role != "owner":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Owner access required")
    return identity


def require_user(identity: Identity = Depends(get_current_identity)) -> Identity:
    if identity.role != "user":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User access required")
    return identity


def require_approved_user(identity: Identity = Depends(require_user)) -> Identity:
    if not identity.group_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Join request not yet approved by your PG owner",
        )
    return identity


def require_group_member(identity: Identity = Depends(get_current_identity)) -> Identity:
    """Either an Owner (always has a group) or an approved User. Used for
    read endpoints (announcements, food, documents, owner contact) that both
    roles are allowed to view within their own PG group."""
    if not identity.group_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not belong to a PG group yet")
    return identity
