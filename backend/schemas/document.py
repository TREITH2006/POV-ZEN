from datetime import datetime

from pydantic import BaseModel, Field


class DocumentOut(BaseModel):
    id: str
    title: str
    category: str
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class DocumentCreateMeta(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    category: str = Field(default="other", max_length=50)
