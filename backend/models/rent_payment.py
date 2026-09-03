from datetime import date, datetime, timezone

from sqlalchemy import String, DateTime, Date, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from utils.ids import new_uuid


class RentPayment(Base):
    __tablename__ = "rent_payments"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)
    rent_id: Mapped[str] = mapped_column(String(32), ForeignKey("rent.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
