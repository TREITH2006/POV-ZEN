from datetime import date, datetime, timezone

from sqlalchemy import String, DateTime, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from utils.ids import new_uuid


class FoodMenu(Base):
    __tablename__ = "food_menus"
    __table_args__ = (UniqueConstraint("group_id", "menu_date", name="uq_group_menu_date"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)
    group_id: Mapped[str] = mapped_column(String(32), ForeignKey("pg_groups.group_id"), nullable=False)
    menu_date: Mapped[date] = mapped_column(Date, nullable=False)
    breakfast: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lunch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dinner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
