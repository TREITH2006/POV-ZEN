from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from utils.ids import new_uuid


class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)
    group_id: Mapped[str] = mapped_column(String(32), ForeignKey("pg_groups.group_id"), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(32), ForeignKey("owners.owner_id"), nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(10), default="normal", nullable=False)  # normal/important/warning
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
