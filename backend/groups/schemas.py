import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class GroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    archived: bool | None = None
    force: bool = False


class MemberResponse(BaseModel):
    id: uuid.UUID
    group_id: uuid.UUID
    user_id: uuid.UUID | None
    email: str
    display_name: str
    joined_at: datetime
    removed_at: datetime | None
    is_pending: bool

    model_config = {"from_attributes": True}


class GroupResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    owner_id: uuid.UUID
    created_at: datetime
    archived_at: datetime | None
    members: list[MemberResponse] = []

    model_config = {"from_attributes": True}


class AddMemberRequest(BaseModel):
    email: EmailStr
