from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from utils.ids import new_code


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_code("USR"))
    account_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("auth_accounts.id"), unique=True, nullable=False
    )
    # Null until a join request is approved.
    group_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("pg_groups.group_id"), nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    room_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sharing_type: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-4
    joined_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    account = relationship("AuthAccount", back_populates="user")
    group = relationship("PGGroup", back_populates="users")
