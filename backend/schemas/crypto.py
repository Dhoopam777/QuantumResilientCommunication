"""Public post-quantum identity metadata schemas."""

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from pydantic import Field


class PublicKeyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kem_public_key: str
    signature_public_key: str
    algorithm_version: str
    created_at: datetime


class DevicePublicKeyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kem_public_key: str = Field(..., min_length=100, max_length=4096)
    signature_public_key: str = Field(..., min_length=100, max_length=8192)
    algorithm_version: str
