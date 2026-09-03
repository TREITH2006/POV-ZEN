from pydantic import BaseModel


class GroupOut(BaseModel):
    group_id: str
    pg_name: str

    model_config = {"from_attributes": True}


class AccessKeyRotateResponse(BaseModel):
    access_key: str
