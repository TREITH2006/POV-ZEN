from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from utils.ids import new_code


class PGGroup(Base):
    __tablename__ = "pg_groups"

    group_id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_code("PG"))
    owner_id: Mapped[str] = mapped_column(String(32), ForeignKey("owners.owner_id"), unique=True, nullable=False)
    pg_name: Mapped[str] = mapped_column(String(150), nullable=False)
    # Secret join credential. Only a bcrypt hash is ever stored; the plaintext
    # key is shown to the Owner exactly once (at creation/rotation time).
    access_key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    owner = relationship("Owner", back_populates="pg_group")
    users = relationship("User", back_populates="group")
