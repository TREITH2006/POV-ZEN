from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

IssueCategory = Literal["plumbing", "electricity", "cleaning", "wifi", "room", "bathroom", "other"]
IssueStatus = Literal["pending", "in_progress", "resolved"]


class IssueCreate(BaseModel):
    room_number: str | None = Field(default=None, max_length=20)
    category: IssueCategory
    description: str = Field(min_length=1, max_length=2000)


class IssueStatusUpdate(BaseModel):
    status: IssueStatus


class IssueOut(BaseModel):
    id: str
    user_id: str
    room_number: str | None
    category: str
    description: str
    image_path: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
