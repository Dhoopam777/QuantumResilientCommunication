"""ML-KEM session metadata stored without derived secret material."""

import secrets
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UUID
from sqlalchemy.orm import Mapped, mapped_column

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
