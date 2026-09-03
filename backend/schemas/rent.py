from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

RentStatus = Literal["paid", "unpaid", "overdue"]


class RentCreate(BaseModel):
    user_id: str
    monthly_rent: float = Field(gt=0)
    due_date: date
    status: RentStatus = "unpaid"


class RentUpdate(BaseModel):
    monthly_rent: float | None = Field(default=None, gt=0)
    due_date: date | None = None
    status: RentStatus | None = None


class RentOut(BaseModel):
    id: str
    user_id: str
    monthly_rent: float
    due_date: date
    status: str

    model_config = {"from_attributes": True}


class RentPaymentCreate(BaseModel):
    amount: float = Field(gt=0)
    payment_date: date
    note: str | None = Field(default=None, max_length=255)


class RentPaymentOut(BaseModel):
    id: str
    rent_id: str
    amount: float
    payment_date: date
    note: str | None

    model_config = {"from_attributes": True}
