from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from auth.dependencies import Identity
from models.issue import Issue
from schemas.issue import IssueCreate, IssueStatusUpdate
from services.storage_service import ALLOWED_IMAGE_TYPES, UnsupportedFileError, save_upload


def create_issue(db: Session, identity: Identity, payload: IssueCreate, image: UploadFile | None) -> Issue:
    image_path = None
    if image is not None:
        contents = image.file.read()
        try:
            image_path = save_upload(image, contents, subfolder="issues", allowed_types=ALLOWED_IMAGE_TYPES)
        except UnsupportedFileError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    issue = Issue(
        user_id=identity.ref_id,
        group_id=identity.group_id,
        room_number=payload.room_number,
        category=payload.category,
        description=payload.description,
        image_path=image_path,
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue


def list_issues_for_user(db: Session, identity: Identity) -> list[Issue]:
    return (
        db.query(Issue)
        .filter(Issue.user_id == identity.ref_id, Issue.group_id == identity.group_id)
        .order_by(Issue.created_at.desc())
        .all()
    )


def list_issues_for_owner(db: Session, identity: Identity) -> list[Issue]:
    return db.query(Issue).filter(Issue.group_id == identity.group_id).order_by(Issue.created_at.desc()).all()


def update_issue_status(db: Session, identity: Identity, issue_id: str, payload: IssueStatusUpdate) -> Issue:
    issue = db.query(Issue).filter(Issue.id == issue_id, Issue.group_id == identity.group_id).first()
    if not issue:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue not found")
    issue.status = payload.status
    db.commit()
    db.refresh(issue)
    return issue
