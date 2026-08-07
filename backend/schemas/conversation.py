"""
Conversation Schemas for Quantum-Resilient Communication System

This module defines Pydantic schemas for Conversation validation and serialization.
"""

import uuid
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConversationCreate(BaseModel):
    """
    Schema for creating a new conversation.
    """
    
    participant_ids: list[uuid.UUID]
    is_group: bool = False
    group_name: Optional[str] = None


class MessagePreview(BaseModel):
    """
    Schema for a preview of the most recent message in a conversation.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sender_id: uuid.UUID
    content_encrypted: str
    message_type: str
    created_at: datetime


class ConversationParticipantInfo(BaseModel):
    """
    Schema for participant info in a conversation response.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    username: str
    display_name: Optional[str] = None
    profile_picture_url: Optional[str] = None
    is_online: bool = False
    last_seen: Optional[datetime] = None
    role: str


class ConversationResponse(BaseModel):
    """
    Schema for conversation responses.
    """
    
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    is_group: bool
    group_name: Optional[str]
    group_description: Optional[str] = None
    group_avatar_url: Optional[str] = None
    created_by: uuid.UUID
    is_encrypted: bool
    created_at: datetime
    updated_at: datetime
    participants: list[ConversationParticipantInfo] = []
    last_message: Optional[MessagePreview] = None


class GroupCreate(BaseModel):
    group_name: str = Field(min_length=1, max_length=255)
    group_description: Optional[str] = Field(default=None, max_length=1000)
    members: list[str] = Field(min_length=1, max_length=100)

    @field_validator("group_name", "group_description")
    @classmethod
    def reject_blank_text(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            raise ValueError("Value must not be blank")
        return value.strip() if value is not None else value

    @field_validator("members")
    @classmethod
    def validate_usernames(cls, value: list[str]) -> list[str]:
        cleaned = [username.strip() for username in value]
        if any(not username or len(username) > 50 for username in cleaned):
            raise ValueError("Invalid username")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("Duplicate members are not allowed")
        return cleaned


class GroupUpdate(BaseModel):
    group_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    group_description: Optional[str] = Field(default=None, max_length=1000)
    group_avatar_url: Optional[str] = Field(default=None, max_length=500)

    @field_validator("group_name", "group_description", "group_avatar_url")
    @classmethod
    def reject_blank_values(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            raise ValueError("Value must not be blank")
        return value.strip() if value is not None else value

    @field_validator("group_avatar_url")
    @classmethod
    def validate_avatar_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        parsed = urlparse(value.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Avatar URL must use http or https")
        return value.strip()


class GroupMemberAdd(BaseModel):
    username: str = Field(min_length=1, max_length=50)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Username must not be blank")
        return value
