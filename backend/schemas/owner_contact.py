from pydantic import BaseModel, EmailStr, Field


class OwnerContactOut(BaseModel):
    name: str
    phone: str | None
    contact_email: EmailStr | None


class OwnerContactUpdate(BaseModel):
    phone: str | None = Field(default=None, max_length=20)
    contact_email: EmailStr | None = None
