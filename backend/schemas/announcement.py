from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

AnnouncementType = Literal["normal", "important", "warning"]


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    message: str = Field(min_length=1)
    type: AnnouncementType = "normal"


class AnnouncementUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=150)
    message: str | None = Field(default=None, min_length=1)
    type: AnnouncementType | None = None


class AnnouncementOut(BaseModel):
    id: str
    title: str
    message: str
    type: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
