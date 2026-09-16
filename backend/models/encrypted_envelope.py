"""
EncryptedEnvelope model for V2 per-recipient-device message ciphertexts.

Each envelope holds one encrypted copy of a message's content, addressed to a
specific recipient device. The server stores the ciphertext but never possesses
the AES key. The recipient device derives the AES key from its own KEM private
key and the associated session's KEM ciphertext.

The `id` is client-generated (UUID) and server-preserved, allowing the client
to include it in the V2 signature payload before sending anything to the server.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base


class EncryptedEnvelope(Base):
    __tablename__ = "encrypted_envelopes"
    __table_args__ = (
        UniqueConstraint(
            "message_id", "recipient_device_id",
            name="uq_envelopes_message_recipient_device",
        ),
        Index("ix_envelopes_recipient_device_id", "recipient_device_id"),
        Index("ix_envelopes_message_id", "message_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        comment="Client-generated envelope ID, server-preserved",
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False, comment="Logical message this envelope belongs to",
    )
    recipient_device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False, comment="Device this envelope is addressed to",
    )
    ciphertext: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="AES-256-GCM ciphertext for this recipient device (base64)",
    )
    nonce: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="12-byte AES-GCM nonce (base64); unique per (key, ciphertext)",
    )
    authentication_tag: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="16-byte AES-GCM authentication tag (base64)",
    )
    encryption_version: Mapped[str | None] = mapped_column(
        String(32), nullable=True,
        comment="Encryption algorithm identifier, e.g. 'AES-256-GCM'",
    )
    ciphertext_hash: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="SHA-256 of ciphertext (hex); binds ciphertext to the message signature",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()",
        comment="When this envelope was created",
    )

    # Relationships
    message: Mapped["Message"] = relationship("Message", back_populates="envelopes")
    recipient_device: Mapped["Device"] = relationship("Device")

    def __repr__(self) -> str:
        return (
            f"<EncryptedEnvelope(id={self.id}, message_id={self.message_id}, "
            f"recipient_device_id={self.recipient_device_id})>"
        )