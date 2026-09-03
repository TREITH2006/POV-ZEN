from pydantic import BaseModel, Field

CURRENT_TERMS_VERSION = "1.0"


class TermsAcceptRequest(BaseModel):
    version: str = Field(default=CURRENT_TERMS_VERSION, max_length=20)
