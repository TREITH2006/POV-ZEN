from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from utils.ids import new_uuid


class JoinRequest(Base):
    __tablename__ = "join_requests"

    request_id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.user_id"), nullable=False)
    group_id: Mapped[str] = mapped_column(String(32), ForeignKey("pg_groups.group_id"), nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="pending", nullable=False)  # pending/approved/rejected
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
