from pydantic import BaseModel, EmailStr, Field


class RegisterOwnerRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone: str | None = Field(default=None, max_length=20)
    pg_name: str = Field(min_length=1, max_length=150)


class RegisterOwnerResponse(BaseModel):
    owner_id: str
    group_id: str
    pg_name: str
    # Shown exactly once. The Owner must copy this and share it out-of-band
    # with residents; it is never retrievable again (only re-rotatable).
    access_key: str


class RegisterUserRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone: str | None = Field(default=None, max_length=20)
    room_number: str | None = Field(default=None, max_length=20)
    sharing_type: int | None = Field(default=None, ge=1, le=4)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class MeResponse(BaseModel):
    account_id: str
    role: str
    ref_id: str
    group_id: str | None
    name: str
