"""
Conversation Model for Quantum-Resilient Communication System

This module defines the Conversation SQLAlchemy model.
"""

import uuid
from typing import Optional
from sqlalchemy import String, Boolean, UUID, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import TimestampMixin
from database.database import Base


class Conversation(Base, TimestampMixin):
    """
    Conversation model for chat conversations between users.

    Attributes:
        id: Unique identifier (UUID)
        is_group: Whether this is a group conversation
        group_name: Name for group conversations (nullable)
        created_by: User ID of the conversation creator
        is_encrypted: End-to-end encryption status
    """

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the conversation"
    )

    is_group: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this is a group conversation"
    )

    group_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Name for group conversations"
    )

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="User who created the conversation"
    )

    is_encrypted: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="End-to-end encryption status"
    )

    # Relationships
    creator: Mapped["User"] = relationship(
        "User",
        back_populates="created_conversations"
    )

    participants: Mapped[list["ConversationParticipant"]] = relationship(
        "ConversationParticipant",
        back_populates="conversation"
    )

    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation"
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, is_group={self.is_group})>"
