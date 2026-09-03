from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from utils.ids import new_uuid


class WebsiteIssue(Base):
    """A report about the POV-ZEN website/application itself — deliberately
    separate from the PG-scoped `issues` table (plumbing/electricity/etc.),
    which is about physical PG maintenance, not the software. Not group-
    scoped: a website bug isn't tied to any one PG, and reporting one must
    work even for a visitor who isn't a member of any group yet."""

    __tablename__ = "website_issues"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    page_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reporter_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
