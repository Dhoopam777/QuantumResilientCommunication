"""
Message Schemas for Quantum-Resilient Communication System

This module defines Pydantic schemas for Message validation and serialization.
"""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class MessageCreate(BaseModel):
    """
    Schema for creating a new message.
    """
    
    conversation_id: uuid.UUID
    content_encrypted: str
    content_hash: str
    message_type: str = "text"
    reply_to: Optional[uuid.UUID] = None


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
    reply_to: Optional[uuid.UUID]
    is_edited: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime