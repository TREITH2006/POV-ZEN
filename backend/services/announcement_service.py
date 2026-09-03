from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from auth.dependencies import Identity
from models.announcement import Announcement
from schemas.announcement import AnnouncementCreate, AnnouncementUpdate


def create_announcement(db: Session, identity: Identity, payload: AnnouncementCreate) -> Announcement:
    announcement = Announcement(
        group_id=identity.group_id,
        owner_id=identity.ref_id,
        title=payload.title,
        message=payload.message,
        type=payload.type,
    )
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return announcement


def list_announcements(db: Session, identity: Identity) -> list[Announcement]:
    return (
        db.query(Announcement)
        .filter(Announcement.group_id == identity.group_id)
        .order_by(Announcement.created_at.desc())
        .all()
    )


def _get_owned(db: Session, identity: Identity, announcement_id: str) -> Announcement:
    announcement = (
        db.query(Announcement)
        .filter(Announcement.id == announcement_id, Announcement.group_id == identity.group_id)
        .first()
    )
    if not announcement:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Announcement not found")
    return announcement


def update_announcement(
    db: Session, identity: Identity, announcement_id: str, payload: AnnouncementUpdate
) -> Announcement:
    announcement = _get_owned(db, identity, announcement_id)
    if payload.title is not None:
        announcement.title = payload.title
    if payload.message is not None:
        announcement.message = payload.message
    if payload.type is not None:
        announcement.type = payload.type
    db.commit()
    db.refresh(announcement)
    return announcement


def delete_announcement(db: Session, identity: Identity, announcement_id: str) -> None:
    announcement = _get_owned(db, identity, announcement_id)
    db.delete(announcement)
    db.commit()
