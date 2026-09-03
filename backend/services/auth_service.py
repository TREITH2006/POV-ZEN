from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from auth.security import create_access_token, hash_password, hash_secret, verify_password
from models.auth_account import AuthAccount
from models.owner import Owner
from models.pg_group import PGGroup
from models.user import User
from schemas.auth import RegisterOwnerRequest, RegisterUserRequest
from utils.ids import new_access_key


def register_owner(db: Session, payload: RegisterOwnerRequest) -> tuple[Owner, PGGroup, str]:
    existing = db.query(AuthAccount).filter(AuthAccount.email == payload.email).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")

    account = AuthAccount(
        email=payload.email,
        password_hash=hash_password(payload.password),
        account_type="owner",
    )
    db.add(account)
    db.flush()

    owner = Owner(account_id=account.id, name=payload.name, phone=payload.phone, contact_email=payload.email)
    db.add(owner)
    db.flush()

    plaintext_access_key = new_access_key()
    group = PGGroup(
        owner_id=owner.owner_id,
        pg_name=payload.pg_name,
        access_key_hash=hash_secret(plaintext_access_key),
    )
    db.add(group)
    db.commit()
    db.refresh(owner)
    db.refresh(group)

    return owner, group, plaintext_access_key


def register_user(db: Session, payload: RegisterUserRequest) -> User:
    existing = db.query(AuthAccount).filter(AuthAccount.email == payload.email).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")

    account = AuthAccount(
        email=payload.email,
        password_hash=hash_password(payload.password),
        account_type="user",
    )
    db.add(account)
    db.flush()

    user = User(
        account_id=account.id,
        name=payload.name,
        phone=payload.phone,
        room_number=payload.room_number,
        sharing_type=payload.sharing_type,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> str:
    """Returns a signed access token, or raises 401."""
    account = db.query(AuthAccount).filter(AuthAccount.email == email).first()
    if not account or not account.password_hash or not verify_password(password, account.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    if account.account_type == "owner":
        owner = db.query(Owner).filter(Owner.account_id == account.id).first()
        ref_id = owner.owner_id
    else:
        user = db.query(User).filter(User.account_id == account.id).first()
        ref_id = user.user_id

    return create_access_token(account_id=account.id, role=account.account_type, ref_id=ref_id)
