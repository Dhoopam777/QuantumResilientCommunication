"""
Conversation Schemas for Quantum-Resilient Communication System

This module defines Pydantic schemas for Conversation validation and serialization.
"""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


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
    created_by: uuid.UUID
    is_encrypted: bool
    created_at: datetime
    updated_at: datetime
    participants: list[ConversationParticipantInfo] = []
    last_message: Optional[MessagePreview] = None
