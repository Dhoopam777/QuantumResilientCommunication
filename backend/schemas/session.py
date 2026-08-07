"""Safe session establishment API schemas."""

from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict


class SessionCreatedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: uuid.UUID
    algorithm: str
    expires_at: datetime


class SessionMetadataResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    algorithm: str
    created_at: datetime
    expires_at: datetime
    status: str
