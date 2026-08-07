"""Public post-quantum identity metadata schemas."""

from pydantic import BaseModel, ConfigDict


class PublicKeyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kem_public_key: str
    signature_public_key: str
    algorithm_version: str
