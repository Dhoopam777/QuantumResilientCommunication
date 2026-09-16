"""
RefreshToken model for device-bound, revocable refresh tokens.

Each row stores a hash of the refresh JWT's random identifier (not the raw
token). A DB dump yields hashes, not usable tokens. Revocation is per-device
or per-token.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("ix_refresh_tokens_device_id", "device_id"),
        Index("ix_refresh_tokens_expires_at", "expires_at"),
        Index("ix_refresh_tokens_is_revoked", "is_revoked"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        comment="Unique identifier for this refresh token record",
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False, comment="Device this refresh token is bound to",
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False,
        comment="SHA-256 hash of the refresh JWT's random identifier (never raw token)",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="When this refresh token expires",
    )
    is_revoked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="True if this refresh token has been revoked",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()",
        comment="When this refresh token was created",
    )

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="refresh_tokens")

    def __repr__(self) -> str:
        return (
            f"<RefreshToken(id={self.id}, device_id={self.device_id}, "
            f"is_revoked={self.is_revoked}, expires_at={self.expires_at})>"
        )