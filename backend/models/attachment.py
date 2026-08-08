"""
Attachment Model for Quantum-Resilient Communication System

This module defines the Attachment SQLAlchemy model for secure file attachments.
"""

import uuid
from typing import Optional

from sqlalchemy import String, Integer, Boolean, UUID, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import TimestampMixin
from database.database import Base


class Attachment(Base, TimestampMixin):
    """
    Attachment model for file uploads (images only in Phase 8.1).

    Security properties:
        - Files stored with UUIDv4 filenames, never client-supplied names
        - Stored outside the web root; accessible only via authenticated API
        - SHA-256 checksum computed server-side for integrity
        - EXIF metadata stripped; images re-encoded before saving
        - Thumbnail generated server-side
        - Soft delete preserves audit trail

    Attributes:
        id: Unique identifier (UUID)
        message_id: Reference to the message this attachment belongs to (nullable until linked)
        conversation_id: Reference to the conversation
        uploader_id: Reference to the user who uploaded
        stored_filename: UUIDv4-based filename on disk (never exposed to other users)
        original_filename: Sanitized original filename (metadata only)
        mime_type: Server-detected MIME type
        file_extension: Lowercase extension including dot, e.g. ".png"
        file_size: File size in bytes
        checksum_sha256: Server-computed SHA-256 hex digest
        width: Image width in pixels (images only)
        height: Image height in pixels (images only)
        thumbnail_filename: UUIDv4-based thumbnail filename on disk
        is_deleted: Soft delete flag
    """

    __tablename__ = "attachments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the attachment"
    )

    message_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
        comment="Message this attachment is linked to (nullable until message is sent)"
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to the conversation"
    )

    uploader_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="User who uploaded this attachment"
    )

    stored_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="UUIDv4-based filename on disk (never exposed to clients)"
    )

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Sanitized original filename (metadata only)"
    )

    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Server-detected MIME type"
    )

    file_extension: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Lowercase extension including dot, e.g. '.png'"
    )

    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="File size in bytes"
    )

    checksum_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Server-computed SHA-256 hex digest"
    )

    width: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Image width in pixels (images only)"
    )

    height: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Image height in pixels (images only)"
    )

    thumbnail_filename: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="UUIDv4-based thumbnail filename on disk"
    )

    encryption_algorithm: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    nonce: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    authentication_tag: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    encrypted_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Soft delete flag"
    )

    # Relationships
    message: Mapped[Optional["Message"]] = relationship(
        "Message",
        back_populates="attachments",
        lazy="selectin"
    )

    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="attachments",
        lazy="selectin"
    )

    uploader: Mapped["User"] = relationship(
        "User",
        back_populates="attachments",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<Attachment(id={self.id}, "
            f"conversation_id={self.conversation_id}, "
            f"mime_type={self.mime_type}, "
            f"file_size={self.file_size})>"
        )
