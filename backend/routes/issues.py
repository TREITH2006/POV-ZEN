from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from auth.dependencies import Identity, require_approved_user, require_group_member, require_owner
from database import get_db
from models.issue import Issue
from schemas.issue import IssueCategory, IssueCreate, IssueOut, IssueStatusUpdate
from services import issue_service
from services.storage_service import resolve_path

router = APIRouter(prefix="/api/issues", tags=["issues"])


@router.post("", response_model=IssueOut, status_code=201)
def create_issue(
    category: IssueCategory = Form(...),
    description: str = Form(..., min_length=1, max_length=2000),
    room_number: str | None = Form(default=None),
    image: UploadFile | None = File(default=None),
    identity: Identity = Depends(require_approved_user),
    db: Session = Depends(get_db),
):
    payload = IssueCreate(category=category, description=description, room_number=room_number)
    return issue_service.create_issue(db, identity, payload, image)


@router.get("/mine", response_model=list[IssueOut])
def list_my_issues(identity: Identity = Depends(require_approved_user), db: Session = Depends(get_db)):
    return issue_service.list_issues_for_user(db, identity)


@router.get("", response_model=list[IssueOut])
def list_group_issues(identity: Identity = Depends(require_owner), db: Session = Depends(get_db)):
    return issue_service.list_issues_for_owner(db, identity)


@router.patch("/{issue_id}/status", response_model=IssueOut)
def update_status(
    issue_id: str,
    payload: IssueStatusUpdate,
    identity: Identity = Depends(require_owner),
    db: Session = Depends(get_db),
):
    return issue_service.update_issue_status(db, identity, issue_id, payload)


@router.get("/{issue_id}/image")
def get_issue_image(
    issue_id: str, identity: Identity = Depends(require_group_member), db: Session = Depends(get_db)
):
    issue = db.query(Issue).filter(Issue.id == issue_id, Issue.group_id == identity.group_id).first()
    if not issue or not issue.image_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Image not found")
    # A regular User may only fetch the image of their own issue; an Owner
    # may fetch any issue image within their own group (already enforced by
    # the group_id filter above).
    if identity.role == "user" and issue.user_id != identity.ref_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Image not found")
    return FileResponse(resolve_path(issue.image_path))
