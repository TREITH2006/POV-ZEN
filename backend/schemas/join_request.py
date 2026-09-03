from datetime import datetime

from pydantic import BaseModel, Field


class JoinRequestCreate(BaseModel):
    access_key: str = Field(min_length=1, max_length=64)


class JoinRequestOut(BaseModel):
    request_id: str
    user_id: str
    user_name: str | None = None
    group_id: str
    status: str
    requested_at: datetime
    decided_at: datetime | None

    model_config = {"from_attributes": True}


class JoinRequestDecision(BaseModel):
    approve: bool
