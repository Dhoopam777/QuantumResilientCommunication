"""
User Model for Quantum-Resilient Communication System

This module defines the User SQLAlchemy model.
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, UUID, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import TimestampMixin
from database.database import Base


class User(Base, TimestampMixin):
    """
    User model for authentication and profile management.
    
    Attributes:
        id: Unique identifier (UUID)
        username: Unique username
        email: Unique email address
        password_hash: Bcrypt hashed password
        full_name: User's full name
        profile_picture_url: URL to profile picture (nullable)
        is_active: Account status
        is_verified: Email verification status
    """
    
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the user"
    )
    
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment="User's display name"
    )
    
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        comment="User's email address"
    )
    
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Bcrypt hashed password"
    )
    
    full_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="User's full name"
    )
    
    profile_picture_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="URL to profile picture"
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Account status"
    )
    
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Email verification status"
    )

    display_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Display name shown to other users"
    )

    bio: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="User biography / about me"
    )

    status_message: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Short status message"
    )

    last_seen: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time the user was seen"
    )

    is_online: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether the user is currently online"
    )
    
    # Relationships
    # user_keys: Mapped[list["UserKey"]] = relationship("UserKey", back_populates="user")
    created_conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="creator"
    )
    conversation_participants: Mapped[list["ConversationParticipant"]] = relationship(
        "ConversationParticipant",
        back_populates="user"
    )
    sent_messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="sender"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"