"""
Message Schemas for Quantum-Resilient Communication System

This module defines Pydantic schemas for Message validation and serialization.
"""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class MessageCreate(BaseModel):
    """
    Schema for creating a new message.
    """

    conversation_id: uuid.UUID
    content_encrypted: str
    content_hash: str
    message_type: str = "text"
    reply_to: Optional[uuid.UUID] = None
    reply_to_message_id: Optional[uuid.UUID] = None


class MessageEdit(BaseModel):
    """
    Schema for editing a message.

    Only the encrypted content and its hash are editable.
    Attachments, replies, and reactions are never modified by an edit.
    """

    content_encrypted: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Encrypted message content (AES-256-GCM)",
    )
    content_hash: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="SHA-256 hash for integrity verification",
    )


class MessageDelete(BaseModel):
    """
    Schema for deleting a message.

    Supports two modes:
    - "me": Hide the message only for the requesting user.
    - "everyone": Soft-delete the message for all participants.
    """

    mode: str = Field(
        ...,
        pattern="^(me|everyone)$",
        description="Deletion mode: 'me' (hide for requesting user) or 'everyone' (soft-delete for all)",
    )


class ReactionCreate(BaseModel):
    """Schema for the fixed, Unicode-only phase 8.2D reaction set."""

    emoji: str = Field(..., min_length=1, max_length=32)


class ReactionUser(BaseModel):
    id: uuid.UUID
    name: str


class ReactionSummary(BaseModel):
    emoji: str
    count: int
    reacted_by_me: bool = False
    users: list[ReactionUser] = Field(default_factory=list)


class ReplyPreview(BaseModel):
    """
    Minimal preview of the message being replied to.
    Included in MessageResponse for rendering reply indicators.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sender_id: uuid.UUID
    content_encrypted: str
    message_type: str
    is_deleted: bool = False
    created_at: datetime


class MessageResponse(BaseModel):
    """
    Schema for message responses.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    content_encrypted: str
    content_hash: str
    message_type: str
    reply_to: Optional[uuid.UUID] = None
    reply_to_message_id: Optional[uuid.UUID] = None
    reply_preview: Optional[ReplyPreview] = None
    is_edited: bool
    edited_at: Optional[datetime] = None
    is_deleted: bool
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[uuid.UUID] = None
    delete_type: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    reactions: list[ReactionSummary] = Field(default_factory=list)
