from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from utils.ids import new_uuid


class TermsAcceptance(Base):
    __tablename__ = "terms_acceptance"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)
    account_id: Mapped[str] = mapped_column(String(32), ForeignKey("auth_accounts.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
