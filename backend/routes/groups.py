from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth.dependencies import Identity, require_group_member, require_owner
from database import get_db
from schemas.group import AccessKeyRotateResponse
from schemas.owner_contact import OwnerContactOut, OwnerContactUpdate
from services import group_service

router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.post("/access-key/rotate", response_model=AccessKeyRotateResponse)
def rotate_access_key(identity: Identity = Depends(require_owner), db: Session = Depends(get_db)):
    key = group_service.rotate_access_key(db, identity)
    return AccessKeyRotateResponse(access_key=key)


@router.get("/users")
def list_group_users(identity: Identity = Depends(require_owner), db: Session = Depends(get_db)):
    users = group_service.list_group_users(db, identity)
    return [
        {
            "user_id": u.user_id,
            "name": u.name,
            "phone": u.phone,
            "room_number": u.room_number,
            "sharing_type": u.sharing_type,
            "joined_date": u.joined_date,
        }
        for u in users
    ]


@router.get("/owner-contact", response_model=OwnerContactOut)
def get_owner_contact(identity: Identity = Depends(require_group_member), db: Session = Depends(get_db)):
    owner = group_service.get_owner_contact(db, identity.group_id)
    return OwnerContactOut(name=owner.name, phone=owner.phone, contact_email=owner.contact_email)


@router.put("/owner-contact", response_model=OwnerContactOut)
def update_owner_contact(
    payload: OwnerContactUpdate, identity: Identity = Depends(require_owner), db: Session = Depends(get_db)
):
    owner = group_service.get_owner_contact(db, identity.group_id)
    if payload.phone is not None:
        owner.phone = payload.phone
    if payload.contact_email is not None:
        owner.contact_email = payload.contact_email
    db.commit()
    db.refresh(owner)
    return OwnerContactOut(name=owner.name, phone=owner.phone, contact_email=owner.contact_email)
