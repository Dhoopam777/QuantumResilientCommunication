"""
LinkToken model for QR / one-time-code device linking.

Issued by the primary device (after security-code verification). One-time use,
short expiry. The code is a random string; it grants authorization for a new
device to join the account. No private keys are ever in this token.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base


class LinkToken(Base):
    __tablename__ = "link_tokens"
    __table_args__ = (
        Index("ix_link_tokens_primary_device_id", "primary_device_id"),
        Index("ix_link_tokens_expires_at", "expires_at"),
        Index("ix_link_tokens_used", "used"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        comment="Unique identifier for this link token",
    )
    primary_device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False, comment="Primary device that issued this token",
    )
    code: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False,
        comment="Random one-time authorization code (QR/OTC)",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="When this link token expires (typically 10 minutes after issue)",
    )
    used: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="True after this link token has been consumed by a new device",
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="When this link token was consumed",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()",
        comment="When this link token was issued",
    )

    # Relationships
    primary_device: Mapped["Device"] = relationship("Device")

    def __repr__(self) -> str:
        return (
            f"<LinkToken(id={self.id}, primary_device_id={self.primary_device_id}, "
            f"used={self.used}, expires_at={self.expires_at})>"
        )