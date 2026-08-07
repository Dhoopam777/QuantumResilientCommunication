"""Privacy-safe conversation request schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConversationRequestCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")


class RequestUser(BaseModel):
    username: str
    display_name: str | None = None
    profile_picture_url: str | None = None
    status: str


class ConversationRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sender: RequestUser
    receiver: RequestUser
    status: str
    created_at: datetime
    updated_at: datetime
