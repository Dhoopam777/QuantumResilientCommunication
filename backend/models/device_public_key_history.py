"""
DevicePublicKeyHistory model for tracking device public key rotation.

Each row records a public key pair (KEM + signature) that was valid for a
device during a specific time window. Used to verify signatures on messages
signed with a device's historical keys after the device rotates its keys.

Public keys only — no private-key fields.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base


class DevicePublicKeyHistory(Base):
    __tablename__ = "device_public_key_history"
    __table_args__ = (
        Index("ix_device_public_key_history_device_id", "device_id"),
        Index("ix_dpk_history_device_valid_from", "device_id", "valid_from"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        comment="Unique identifier for this public key history record",
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False, comment="Device whose historical public key this records",
    )
    kem_public_key: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="ML-KEM-768 public key at that time (base64). Public only.",
    )
    signature_public_key: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="ML-DSA-65 signature public key at that time (base64). Public only.",
    )
    algorithm_version: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="Algorithm identifier, e.g. 'ML-KEM-768+ML-DSA-65'",
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="When this key became valid for the device",
    )
    valid_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="When superseded (NULL = currently valid)",
    )

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="public_key_history")

    def __repr__(self) -> str:
        return (
            f"<DevicePublicKeyHistory(id={self.id}, device_id={self.device_id}, "
            f"valid_from={self.valid_from}, valid_to={self.valid_to})>"
        )