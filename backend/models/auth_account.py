from datetime import datetime, timezone

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from utils.ids import new_uuid


class AuthAccount(Base):
    """Central identity record. Owners and Users each hold a 1:1 FK to this table
    so authentication logic stays fully separate from business/role logic."""

    __tablename__ = "auth_accounts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    account_type: Mapped[str] = mapped_column(String(10), nullable=False)  # "owner" | "user"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    owner = relationship("Owner", back_populates="account", uselist=False)
    user = relationship("User", back_populates="account", uselist=False)
