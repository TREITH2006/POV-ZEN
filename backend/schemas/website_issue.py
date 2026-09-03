from pydantic import BaseModel, EmailStr, Field


class WebsiteIssueCreate(BaseModel):
    description: str = Field(min_length=1, max_length=2000)
    page_url: str | None = Field(default=None, max_length=500)
    reporter_email: EmailStr | None = None
