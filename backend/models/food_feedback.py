from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from utils.ids import new_uuid


class FoodFeedback(Base):
    __tablename__ = "food_feedback"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)
    menu_id: Mapped[str] = mapped_column(String(32), ForeignKey("food_menus.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.user_id"), nullable=False)
    group_id: Mapped[str] = mapped_column(String(32), ForeignKey("pg_groups.group_id"), nullable=False)
    rating: Mapped[str] = mapped_column(String(10), nullable=False)  # good/average/bad
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
