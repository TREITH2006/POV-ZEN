from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from database import get_db
from rate_limit import limiter
from schemas.website_issue import WebsiteIssueCreate
from services import website_issue_service

router = APIRouter(prefix="/api/website-issues", tags=["website-issues"])


@router.post("", status_code=201)
@limiter.limit("5/minute")
def report_website_issue(request: Request, payload: WebsiteIssueCreate, db: Session = Depends(get_db)):
    # Deliberately open to unauthenticated visitors too — a website bug
    # (e.g. "the login button doesn't work") must be reportable even by
    # someone who can't log in because of it. Rate-limited against spam.
    website_issue_service.create_website_issue(db, payload)
    return {"status": "received"}
