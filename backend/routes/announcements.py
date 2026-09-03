from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth.dependencies import Identity, require_group_member, require_owner
from database import get_db
from schemas.announcement import AnnouncementCreate, AnnouncementOut, AnnouncementUpdate
from services import announcement_service

router = APIRouter(prefix="/api/announcements", tags=["announcements"])


@router.post("", response_model=AnnouncementOut, status_code=201)
def create_announcement(
    payload: AnnouncementCreate, identity: Identity = Depends(require_owner), db: Session = Depends(get_db)
):
    return announcement_service.create_announcement(db, identity, payload)


@router.get("", response_model=list[AnnouncementOut])
def list_announcements(identity: Identity = Depends(require_group_member), db: Session = Depends(get_db)):
    return announcement_service.list_announcements(db, identity)


@router.put("/{announcement_id}", response_model=AnnouncementOut)
def update_announcement(
    announcement_id: str,
    payload: AnnouncementUpdate,
    identity: Identity = Depends(require_owner),
    db: Session = Depends(get_db),
):
    return announcement_service.update_announcement(db, identity, announcement_id, payload)


@router.delete("/{announcement_id}", status_code=204)
def delete_announcement(
    announcement_id: str, identity: Identity = Depends(require_owner), db: Session = Depends(get_db)
):
    announcement_service.delete_announcement(db, identity, announcement_id)
