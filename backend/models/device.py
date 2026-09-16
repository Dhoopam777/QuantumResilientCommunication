"""
Device model for multi-device support.

A Device represents a specific browser/device instance registered to a user
account. Each device has its own PQC identity keypair (public keys stored
here; private keys never leave the client and are never stored on the server).
"""

import uuid
from datetime import datetime

from sqlalchemy import text as sa_text
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base
from models.base import TimestampMixin


class Device(Base, TimestampMixin):
    __tablename__ = "devices"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'active', 'revoked', 'lost')",
            name="ck_devices_status",
        ),
        Index("ix_devices_user_id", "user_id"),
        Index("ix_devices_status", "status"),
        Index("ix_devices_last_seen_at", "last_seen_at"),
        Index(
            "uq_devices_one_primary_per_user",
            "user_id",
            unique=True,
            postgresql_where=sa_text("is_primary = true"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        comment="Server-assigned device record identifier (authoritative device_id)",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, comment="Owning user account",
    )
    device_uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False,
        comment="Client-generated stable device identity",
    )
    name: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Human label chosen by the user",
    )
    device_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="'web', 'desktop', or 'mobile'",
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="True if this is the user's primary device (one per user)",
    )
    kem_public_key: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="ML-KEM-768 public key (base64). Public only.",
    )
    signature_public_key: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="ML-DSA-65 public key (base64). Public only.",
    )
    algorithm_version: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="Algorithm version string",
    )
    key_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Client-reported timestamp when keypair was generated",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
        comment="Lifecycle: 'pending', 'active', 'revoked', or 'lost'",
    )
    authorized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="When this device was authorized by primary/recovery",
    )
    authorized_by_device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="SET NULL"),
        nullable=True, comment="Device that authorized this one (NULL for self/recovery)",
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Last successful auth/refresh timestamp",
    )
    security_code_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Last time this device verified the account security code",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="devices")

    authorizing_device: Mapped["Device | None"] = relationship(
        "Device", remote_side="Device.id",
        foreign_keys=[authorized_by_device_id], lazy="selectin",
    )
    authorized_devices: Mapped[list["Device"]] = relationship(
        "Device", back_populates="authorizing_device",
        foreign_keys=[authorized_by_device_id], lazy="selectin",
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="device",
        cascade="all, delete-orphan", lazy="selectin",
    )
    public_key_history: Mapped[list["DevicePublicKeyHistory"]] = relationship(
        "DevicePublicKeyHistory", back_populates="device",
        cascade="all, delete-orphan", lazy="selectin",
    )
    sessions_as_initiator: Mapped[list["SessionKey"]] = relationship(
        "SessionKey", back_populates="initiator_device", lazy="selectin",
    )
    sessions_as_recipient: Mapped[list["SessionKey"]] = relationship(
        "SessionKey", back_populates="recipient_device", lazy="selectin",
    )
    signed_messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="sender_device", lazy="selectin",
    )
    signed_attachments: Mapped[list["Attachment"]] = relationship(
        "Attachment", back_populates="sender_device", lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<Device(id={self.id}, user_id={self.user_id}, "
            f"device_uuid={self.device_uuid}, status={self.status}, "
            f"is_primary={self.is_primary})>"
        )