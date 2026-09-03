from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from auth.dependencies import Identity, get_current_identity
from auth.security import COOKIE_NAME
from config import get_settings
from database import get_db
from models.owner import Owner
from models.user import User
from rate_limit import limiter
from schemas.auth import (
    LoginRequest,
    MeResponse,
    RegisterOwnerRequest,
    RegisterOwnerResponse,
    RegisterUserRequest,
)
from services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


def _set_auth_cookie(response: Response, token: str) -> None:
    # SameSite is configurable (COOKIE_SAMESITE) for deployments where the
    # frontend and API are not same-site — see config.py for guidance. A
    # browser refuses to send SameSite=None cookies over plain HTTP anyway,
    # but the Secure flag is force-enabled here regardless of ENVIRONMENT so
    # a misconfigured .env can't silently produce a cookie the browser drops.
    # No `domain=` is set, so the cookie is host-only and scoped to whichever
    # exact host issued it.
    samesite = settings.cookie_samesite.lower()
    secure = settings.is_production or samesite == "none"
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=secure,
        samesite=samesite,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )


@router.post("/register/owner", response_model=RegisterOwnerResponse, status_code=201)
@limiter.limit("5/minute")
def register_owner(request: Request, payload: RegisterOwnerRequest, response: Response, db: Session = Depends(get_db)):
    owner, group, access_key = auth_service.register_owner(db, payload)
    token = auth_service.authenticate(db, payload.email, payload.password)
    _set_auth_cookie(response, token)
    return RegisterOwnerResponse(
        owner_id=owner.owner_id, group_id=group.group_id, pg_name=group.pg_name, access_key=access_key
    )


@router.post("/register/user", status_code=201)
@limiter.limit("5/minute")
def register_user(request: Request, payload: RegisterUserRequest, response: Response, db: Session = Depends(get_db)):
    user = auth_service.register_user(db, payload)
    token = auth_service.authenticate(db, payload.email, payload.password)
    _set_auth_cookie(response, token)
    return {"user_id": user.user_id}


@router.post("/login")
@limiter.limit("10/minute")
def login(request: Request, payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    token = auth_service.authenticate(db, payload.email, payload.password)
    _set_auth_cookie(response, token)
    return {"status": "ok"}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"status": "ok"}


@router.get("/me", response_model=MeResponse)
def me(identity: Identity = Depends(get_current_identity), db: Session = Depends(get_db)):
    if identity.role == "owner":
        name = db.get(Owner, identity.ref_id).name
    else:
        name = db.get(User, identity.ref_id).name
    return MeResponse(
        account_id=identity.account_id,
        role=identity.role,
        ref_id=identity.ref_id,
        group_id=identity.group_id,
        name=name,
    )
