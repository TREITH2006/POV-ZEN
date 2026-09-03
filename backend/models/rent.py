from datetime import date, datetime, timezone

from sqlalchemy import String, DateTime, Date, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from utils.ids import new_uuid


class Rent(Base):
    __tablename__ = "rent"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.user_id"), nullable=False)
    group_id: Mapped[str] = mapped_column(String(32), ForeignKey("pg_groups.group_id"), nullable=False)
    monthly_rent: Mapped[float] = mapped_column(Float, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="unpaid", nullable=False)  # paid/unpaid/overdue
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
