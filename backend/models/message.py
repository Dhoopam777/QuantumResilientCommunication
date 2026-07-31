"""
Message Model for Quantum-Resilient Communication System

This module defines the Message SQLAlchemy model.
"""

import uuid
from typing import Optional
from sqlalchemy import String, Boolean, UUID, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import TimestampMixin
from database.database import Base


class Message(Base, TimestampMixin):
    """
    Message model for individual messages within conversations.

    Attributes:
        id: Unique identifier (UUID)
        conversation_id: Reference to the conversation
        sender_id: Reference to the user who sent the message
        content_encrypted: Encrypted message content (AES-256-GCM)
        content_hash: SHA-256 hash for integrity verification
        message_type: Type of message ('text', 'image', 'file', 'audio', 'system')
        reply_to: Parent message ID if this is a reply (no relationship yet)
        is_edited: Whether the message has been edited
        is_deleted: Soft delete flag
    """

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the message"
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Reference to the conversation"
    )

    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="User who sent the message"
    )

    content_encrypted: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Encrypted message content (AES-256-GCM)"
    )

    content_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="SHA-256 hash for integrity verification"
    )

    message_type: Mapped[str] = mapped_column(
        String(20),
        default="text",
        nullable=False,
        comment="Type: 'text', 'image', 'file', 'audio', 'system'"
    )

    reply_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Parent message ID if reply (no FK relationship yet)"
    )

    is_edited: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Edit status"
    )

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Soft delete flag"
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages"
    )

    sender: Mapped["User"] = relationship(
        "User",
        back_populates="sent_messages"
    )

    def __repr__(self) -> str:
        return (
            f"<Message(id={self.id}, "
            f"conversation_id={self.conversation_id}, "
            f"message_type={self.message_type})>"
        )