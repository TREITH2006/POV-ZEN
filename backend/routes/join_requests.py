from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from auth.dependencies import Identity, require_owner, require_user
from database import get_db
from models.user import User
from rate_limit import limiter
from schemas.join_request import JoinRequestCreate, JoinRequestDecision, JoinRequestOut
from services import join_service

router = APIRouter(prefix="/api/join-requests", tags=["join-requests"])


@router.post("", response_model=JoinRequestOut, status_code=201)
@limiter.limit("10/minute")
def submit_join_request(
    request: Request,
    payload: JoinRequestCreate,
    identity: Identity = Depends(require_user),
    db: Session = Depends(get_db),
):
    request = join_service.submit_join_request(db, identity, payload.access_key)
    return JoinRequestOut.model_validate(request)


@router.get("/mine", response_model=JoinRequestOut | None)
def get_my_latest_request(identity: Identity = Depends(require_user), db: Session = Depends(get_db)):
    request = join_service.get_latest_request_for_user(db, identity)
    return JoinRequestOut.model_validate(request) if request else None


@router.get("", response_model=list[JoinRequestOut])
def list_pending_requests(identity: Identity = Depends(require_owner), db: Session = Depends(get_db)):
    requests = join_service.list_requests_for_owner(db, identity)
    out = []
    for r in requests:
        user = db.get(User, r.user_id)
        item = JoinRequestOut.model_validate(r)
        item.user_name = user.name if user else None
        out.append(item)
    return out


@router.patch("/{request_id}/decision", response_model=JoinRequestOut)
def decide_request(
    request_id: str,
    payload: JoinRequestDecision,
    identity: Identity = Depends(require_owner),
    db: Session = Depends(get_db),
):
    request = join_service.decide_request(db, identity, request_id, payload.approve)
    return JoinRequestOut.model_validate(request)
