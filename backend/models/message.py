"""
Message Model for Quantum-Resilient Communication System

This module defines the Message SQLAlchemy model.
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, UUID, Text, ForeignKey, DateTime
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
        reply_to: Parent message ID if this is a reply (legacy field)
        reply_to_message_id: Parent message FK (self-referential)
        is_edited: Whether the message has been edited
        edited_at: Timestamp when the message was last edited (NULL if never edited)
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
        comment="Parent message ID if reply (legacy field, use reply_to_message_id)"
    )

    reply_to_message_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="RESTRICT"),
        nullable=True,
        comment="Parent message this message replies to (FK to messages.id)"
    )

    is_edited: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Edit status"
    )

    edited_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when the message was last edited (NULL if never edited)"
    )

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Soft delete flag"
    )

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when the message was deleted (NULL if not deleted)"
    )

    deleted_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="User who initiated the deletion (NULL if not deleted)"
    )

    delete_type: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Deletion mode: 'me' (hidden for requesting user) or 'everyone' (hidden for all)"
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

    attachments: Mapped[list["Attachment"]] = relationship(
        "Attachment",
        back_populates="message"
    )

    # Self-referential relationship for replies
    reply_to_message: Mapped[Optional["Message"]] = relationship(
        "Message",
        remote_side="Message.id",
        foreign_keys=[reply_to_message_id],
        back_populates="replies",
        lazy="selectin",
    )

    replies: Mapped[list["Message"]] = relationship(
        "Message",
        foreign_keys=[reply_to_message_id],
        back_populates="reply_to_message",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<Message(id={self.id}, "
            f"conversation_id={self.conversation_id}, "
            f"message_type={self.message_type})>"
        )