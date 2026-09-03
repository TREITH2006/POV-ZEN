from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from utils.ids import new_code


class Owner(Base):
    __tablename__ = "owners"

    owner_id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_code("OWN"))
    account_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("auth_accounts.id"), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    account = relationship("AuthAccount", back_populates="owner")
    pg_group = relationship("PGGroup", back_populates="owner", uselist=False)
