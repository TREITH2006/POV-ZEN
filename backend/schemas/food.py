from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

Rating = Literal["good", "average", "bad"]


class FoodMenuCreate(BaseModel):
    menu_date: date
    breakfast: str | None = Field(default=None, max_length=255)
    lunch: str | None = Field(default=None, max_length=255)
    dinner: str | None = Field(default=None, max_length=255)


class FoodMenuUpdate(BaseModel):
    breakfast: str | None = Field(default=None, max_length=255)
    lunch: str | None = Field(default=None, max_length=255)
    dinner: str | None = Field(default=None, max_length=255)


class FoodMenuOut(BaseModel):
    id: str
    menu_date: date
    breakfast: str | None
    lunch: str | None
    dinner: str | None

    model_config = {"from_attributes": True}


class FoodFeedbackCreate(BaseModel):
    rating: Rating
    comment: str | None = Field(default=None, max_length=1000)


class FoodFeedbackOut(BaseModel):
    id: str
    menu_id: str
    user_id: str
    rating: str
    comment: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
