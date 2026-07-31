"""
Message Service for Quantum-Resilient Communication System

This module provides business logic for message operations.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models.message import Message
from models.conversation import Conversation
from services.conversation_service import is_participant
from sqlalchemy import asc


class MessageService:
    """Service class for message-related operations."""

    VALID_MESSAGE_TYPES = {"text", "image", "file", "audio", "system"}

    @staticmethod
    def send_message(
        db: Session,
        conversation_id: uuid.UUID,
        sender_id: uuid.UUID,
        content_encrypted: str,
        content_hash: str,
        message_type: str = "text",
        reply_to: Optional[uuid.UUID] = None,
    ) -> Message:
        """
        Send a message in a conversation.

        Validates that the sender is an active participant, creates the message,
        and updates the conversation's updated_at timestamp. All operations are
        performed in a single transaction.

        Args:
            db: Database session
            conversation_id: UUID of the conversation
            sender_id: UUID of the message sender
            content_encrypted: Encrypted message content (AES-256-GCM)
            content_hash: SHA-256 hash for integrity verification
            message_type: Type of message ('text', 'image', 'file', 'audio', 'system')
            reply_to: Parent message ID if this is a reply (optional, not validated yet)

        Returns:
            Message: The created message object

        Raises:
            ValueError: If:
                - Sender is not an active participant
                - content_encrypted is empty
                - content_hash is empty
                - message_type is invalid
        """
        # Validate inputs
        if not content_encrypted or not content_encrypted.strip():
            raise ValueError("Message content cannot be empty")

        if not content_hash or not content_hash.strip():
            raise ValueError("Content hash cannot be empty")

        if message_type not in MessageService.VALID_MESSAGE_TYPES:
            raise ValueError(
                f"Invalid message type '{message_type}'. "
                f"Allowed types: {', '.join(sorted(MessageService.VALID_MESSAGE_TYPES))}"
            )

        # Verify sender is an active participant
        if not is_participant(db, conversation_id, sender_id):
            raise ValueError("Sender is not a participant in this conversation")

        # Create the message
        message = Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            content_encrypted=content_encrypted,
            content_hash=content_hash,
            message_type=message_type,
            reply_to=reply_to,
        )
        db.add(message)

        # Update conversation's updated_at timestamp
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conversation:
            conversation.updated_at = datetime.now(timezone.utc)

        # Commit the transaction
        try:
            db.commit()
            db.refresh(message)
            return message
        except Exception:
            db.rollback()
            raise


    @staticmethod
    def get_message_by_id(db: Session, message_id: uuid.UUID) -> Optional[Message]:
        """
        Retrieve a message by its ID.

        Args:
            db: Database session
            message_id: UUID of the message

        Returns:
            Message object if found, None otherwise
        """
        return db.query(Message).filter(Message.id == message_id).first()

    @staticmethod
    def get_conversation_messages(
        db: Session,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Message]:
        """
        Retrieve messages for a conversation with pagination.

        Verifies the user is an active participant, then returns non-deleted messages
        ordered by created_at ASC with limit/offset pagination.

        Args:
            db: Database session
            conversation_id: UUID of the conversation
            user_id: UUID of the requesting user
            limit: Maximum number of messages to return (1-100, default: 50)
            offset: Number of messages to skip (default: 0)

        Returns:
            List of Message objects ordered by created_at ASC

        Raises:
            ValueError: If:
                - User is not an active participant
                - limit <= 0
                - limit > 100
                - offset < 0
        """
        # Validate pagination parameters
        if limit <= 0:
            raise ValueError("Limit must be greater than 0")
        if limit > 100:
            raise ValueError("Limit cannot exceed 100")
        if offset < 0:
            raise ValueError("Offset cannot be negative")

        # Verify user is an active participant
        if not is_participant(db, conversation_id, user_id):
            raise ValueError("User is not a participant in this conversation")

        # Query messages
        return (
            db.query(Message)
            .filter(
                Message.conversation_id == conversation_id,
                Message.is_deleted == False,  # noqa: E712
            )
            .order_by(asc(Message.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )


# Convenience functions for direct usage
def send_message(
    db: Session,
    conversation_id: uuid.UUID,
    sender_id: uuid.UUID,
    content_encrypted: str,
    content_hash: str,
    message_type: str = "text",
    reply_to: Optional[uuid.UUID] = None,
) -> Message:
    """Convenience function to send a message."""
    return MessageService.send_message(
        db=db,
        conversation_id=conversation_id,
        sender_id=sender_id,
        content_encrypted=content_encrypted,
        content_hash=content_hash,
        message_type=message_type,
        reply_to=reply_to,
    )


def get_message_by_id(db: Session, message_id: uuid.UUID) -> Optional[Message]:
    """Convenience function to get a message by ID."""
    return MessageService.get_message_by_id(db, message_id)


def get_conversation_messages(
    db: Session,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[Message]:
    """Convenience function to get conversation messages with pagination."""
    return MessageService.get_conversation_messages(
        db=db,
        conversation_id=conversation_id,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )
