"""Safe session establishment API schemas."""

from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class SessionCreatedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: uuid.UUID
    algorithm: str
    expires_at: datetime


class SessionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kem_ciphertext: str = Field(..., min_length=1, max_length=4096)


class SessionMetadataResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    algorithm: str
    created_at: datetime
    expires_at: datetime
    status: str
    session_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    kem_ciphertext: str | None = None
