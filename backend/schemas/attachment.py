"""
Pydantic Schemas for Attachments

Defines response schemas for the attachment API. No sensitive fields
(stored_filename, checksum) are exposed in the standard response.
"""

from datetime import datetime
from typing import Optional

import uuid
from pydantic import BaseModel, Field


class AttachmentResponse(BaseModel):
    """
    Standard attachment response returned to clients.
    Never includes internal storage details (stored_filename, checksum).
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    message_id: Optional[uuid.UUID] = None
    conversation_id: uuid.UUID
    uploader_id: uuid.UUID
    original_filename: str
    mime_type: str
    file_extension: str
    file_size: int
    width: Optional[int] = None
    height: Optional[int] = None
    thumbnail_url: Optional[str] = None  # relative API path
    created_at: datetime


class AttachmentUploadResponse(AttachmentResponse):
    """
    Response returned immediately after upload.
    Includes the SHA-256 checksum for client-side verification.
    """

    checksum_sha256: str = Field(..., description="Server-computed SHA-256 hex digest")


class AttachmentUploadRequest(BaseModel):
    """Metadata sent alongside the file upload (as form fields)."""

    conversation_id: uuid.UUID = Field(..., description="Conversation to attach to")
