from sqlalchemy.orm import Session

from models.website_issue import WebsiteIssue
from schemas.website_issue import WebsiteIssueCreate


def create_website_issue(db: Session, payload: WebsiteIssueCreate) -> WebsiteIssue:
    issue = WebsiteIssue(
        description=payload.description,
        page_url=payload.page_url,
        reporter_email=payload.reporter_email,
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue
