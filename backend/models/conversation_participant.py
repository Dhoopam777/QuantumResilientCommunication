"""
ConversationParticipant Model for Quantum-Resilient Communication System

This module defines the ConversationParticipant SQLAlchemy model.
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, UUID, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import TimestampMixin
from database.database import Base


class ConversationParticipant(Base, TimestampMixin):
    """
    Junction model for many-to-many relationship between users and conversations.

    Attributes:
        id: Unique identifier (UUID)
        conversation_id: Reference to the conversation
        user_id: Reference to the user
        role: Participant role ('admin', 'member')
        joined_at: When the user joined the conversation
        last_read_message_id: Last message read by user (nullable, no relationship yet)
        last_read_at: Timestamp of last read
        is_muted: Notification mute status
        left_at: When user left (NULL if still a member)
    """

    __tablename__ = "conversation_participants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the participant record"
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Reference to the conversation"
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Reference to the user"
    )

    role: Mapped[str] = mapped_column(
        String(20),
        default="member",
        nullable=False,
        comment="Participant role: 'admin' or 'member'"
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When the user joined the conversation"
    )

    last_read_message_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Last message read by user (no FK relationship yet)"
    )

    last_read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last read"
    )

    is_muted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Notification mute status"
    )

    left_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When user left the conversation (NULL if still a member)"
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="participants"
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="conversation_participants"
    )

    def __repr__(self) -> str:
        return (
            f"<ConversationParticipant(id={self.id}, "
            f"conversation_id={self.conversation_id}, "
            f"user_id={self.user_id})>"
        )