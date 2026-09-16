"""ML-KEM session metadata stored without derived secret material."""

import secrets
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base
from models.base import TimestampMixin


def _secure_uuid() -> uuid.UUID:
    return uuid.UUID(bytes=secrets.token_bytes(16), version=4)


class SessionKey(Base, TimestampMixin):
    __tablename__ = "session_keys"
    __table_args__ = (
        Index("ix_session_keys_conversation_id", "conversation_id"),
        Index("ix_session_keys_initiator_id", "initiator_id"),
        Index("ix_session_keys_recipient_id", "recipient_id"),
        Index("ix_session_keys_expires_at", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_secure_uuid
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="RESTRICT"), nullable=False
    )
    initiator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    kem_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    session_key_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False, default=_secure_uuid
    )
    algorithm: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # V2 device-level identity (nullable for backward compatibility with V1 sessions)
    initiator_device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="SET NULL"),
        nullable=True,
        comment="Device that initiated this session (V2; NULL for V1 sessions)",
    )
    recipient_device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="SET NULL"),
        nullable=True,
        comment="Device this session is addressed to (V2; NULL for V1 sessions)",
    )

    # Relationships
    initiator_device: Mapped["Device | None"] = relationship(
        "Device",
        foreign_keys=[initiator_device_id],
        back_populates="sessions_as_initiator",
        lazy="selectin",
    )
    recipient_device: Mapped["Device | None"] = relationship(
        "Device",
        foreign_keys=[recipient_device_id],
        back_populates="sessions_as_recipient",
        lazy="selectin",
    )
