from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from utils.ids import new_uuid


class JoinRequest(Base):
    __tablename__ = "join_requests"
    __table_args__ = (
        # DB-level backstop for "at most one pending request per user, across
        # all groups": a partial unique index means even a genuine concurrent
        # race (two submissions landing between the application-level check
        # and its commit) fails at the database rather than corrupting state.
        # Supported identically on SQLite (tests/local dev) and PostgreSQL.
        Index(
            "uq_one_pending_request_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
            sqlite_where=text("status = 'pending'"),
        ),
    )

    request_id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.user_id"), nullable=False)
    group_id: Mapped[str] = mapped_column(String(32), ForeignKey("pg_groups.group_id"), nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="pending", nullable=False)  # pending/approved/rejected
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
