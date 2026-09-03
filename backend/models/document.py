from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from utils.ids import new_uuid


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)
    group_id: Mapped[str] = mapped_column(String(32), ForeignKey("pg_groups.group_id"), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(32), ForeignKey("owners.owner_id"), nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="other", nullable=False)
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
