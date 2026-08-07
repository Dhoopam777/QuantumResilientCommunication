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
from models.user import User
from models.attachment import Attachment
from services.crypto_service import CryptoService
from core.config import settings
from services.conversation_service import is_participant
from sqlalchemy import asc


class MessageService:
    """Service class for message-related operations."""

    VALID_MESSAGE_TYPES = {"text", "image", "file", "audio", "system"}

    @staticmethod
    def _validate_reply_target(
        db: Session,
        conversation_id: uuid.UUID,
        reply_to_message_id: Optional[uuid.UUID],
    ) -> None:
        """
        Validate that the reply target message exists and belongs to the same conversation.

        Prevents:
        - Replying to messages in other conversations (cross-conversation replies)
        - Replying to non-existent messages
        - Circular references (replying to a message that replies to this one)

        Soft-deleted parent messages are allowed — the reply relationship is preserved.

        Args:
            db: Database session
            conversation_id: UUID of the conversation the reply is being sent to
            reply_to_message_id: UUID of the parent message being replied to

        Raises:
            ValueError: If the reply target is invalid
        """
        if reply_to_message_id is None:
            return

        # Load the parent message (including soft-deleted ones)
        parent = db.query(Message).filter(Message.id == reply_to_message_id).first()

        if parent is None:
            raise ValueError("Reply target message does not exist")

        # Prevent cross-conversation replies
        if parent.conversation_id != conversation_id:
            raise ValueError("Cannot reply to a message in a different conversation")

        # Prevent circular references: the parent must not reply to the new message.
        # Since the new message doesn't exist yet, we check the parent's reply chain
        # to ensure it doesn't create a cycle. A message cannot reply to itself.
        # Note: parent.id == reply_to_message_id is always true here (parent was
        # loaded by that ID), so we check the parent's own reply chain instead.
        if parent.reply_to_message_id == reply_to_message_id:
            raise ValueError("Cannot reply to a message with itself")

    @staticmethod
    def send_message(
        db: Session,
        conversation_id: uuid.UUID,
        sender_id: uuid.UUID,
        content_encrypted: str,
        content_hash: str,
        message_type: str = "text",
        reply_to: Optional[uuid.UUID] = None,
        reply_to_message_id: Optional[uuid.UUID] = None,
        attachment_ids: Optional[list[uuid.UUID]] = None,
        attachments_metadata: Optional[list[dict]] = None,
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
            reply_to: Parent message ID if this is a reply (legacy field)
            reply_to_message_id: Parent message FK (self-referential)

        Returns:
            Message: The created message object

        Raises:
            ValueError: If:
                - Sender is not an active participant
                - content_encrypted is empty
                - content_hash is empty
                - message_type is invalid
                - Reply target is invalid (cross-conversation, non-existent, circular)
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

        # Validate reply target (if any)
        MessageService._validate_reply_target(db, conversation_id, reply_to_message_id)

        signature_created_at = datetime.now(timezone.utc)
        sender = db.query(User).filter(User.id == sender_id).first()
        attachments = []
        if attachment_ids:
            attachments = (
                db.query(Attachment)
                .filter(
                    Attachment.id.in_(attachment_ids),
                    Attachment.conversation_id == conversation_id,
                    Attachment.uploader_id == sender_id,
                    Attachment.message_id.is_(None),
                    Attachment.is_deleted.is_(False),
                )
                .all()
            )
            if len(attachments) != len(set(attachment_ids)):
                raise ValueError("Invalid attachment")
            attachments_metadata = [
                {
                    "id": str(attachment.id),
                    "original_filename": attachment.original_filename,
                    "mime_type": attachment.mime_type,
                    "file_size": attachment.file_size,
                    "checksum_sha256": attachment.checksum_sha256,
                    "width": attachment.width,
                    "height": attachment.height,
                }
                for attachment in attachments
            ]
        signature = None
        signature_algorithm = None
        if settings.PQC_ENABLED:
            if sender is None:
                raise ValueError("Message authentication failed")
            try:
                signature = CryptoService.sign_message(
                    sender,
                    conversation_id,
                    message_type,
                    content_encrypted,
                    signature_created_at,
                    attachments_metadata,
                )
            except (RuntimeError, ValueError):
                raise ValueError("Message authentication failed")
        # Create the message
        message = Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            content_encrypted=content_encrypted,
            content_hash=content_hash,
            message_type=message_type,
            reply_to=reply_to,
            reply_to_message_id=reply_to_message_id,
            created_at=signature_created_at,
            signature=signature,
            signature_algorithm="ML-DSA-65" if signature else None,
            signature_created_at=signature_created_at if signature else None,
        )
        db.add(message)
        db.flush()
        for attachment in attachments:
            attachment.message_id = message.id

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
    def edit_message(
        db: Session,
        message_id: uuid.UUID,
        user_id: uuid.UUID,
        content_encrypted: str,
        content_hash: str,
    ) -> Message:
        """
        Edit a message's text content.

        Security model:
        - Only the message owner (sender) can edit their own message.
        - The user must be an active participant in the message's conversation.
        - Deleted messages cannot be edited.
        - System messages cannot be edited.
        - Only text content is updated — attachments, replies, and reactions
          are never modified by an edit.

        Args:
            db: Database session
            message_id: UUID of the message to edit
            user_id: UUID of the user attempting the edit
            content_encrypted: New encrypted message content
            content_hash: New SHA-256 hash for integrity verification

        Returns:
            Message: The updated message object

        Raises:
            ValueError: If:
                - Message does not exist
                - Message is deleted
                - Message is a system message
                - User is not the message owner
                - User is not an active participant in the conversation
                - content_encrypted is empty or whitespace-only
                - content_hash is empty
        """
        # Validate inputs
        if not content_encrypted or not content_encrypted.strip():
            raise ValueError("Message content cannot be empty")

        if not content_hash or not content_hash.strip():
            raise ValueError("Content hash cannot be empty")

        # Load the message
        message = db.query(Message).filter(Message.id == message_id).first()
        if message is None:
            raise ValueError("Message not found")

        # Reject editing deleted messages
        if message.is_deleted:
            raise ValueError("Cannot edit a deleted message")

        # Reject editing system messages
        if message.message_type == "system":
            raise ValueError("Cannot edit a system message")

        # Ownership verification — only the sender can edit their own message
        if message.sender_id != user_id:
            raise ValueError("You can only edit your own messages")

        # Conversation authorization — user must be an active participant
        if not is_participant(db, message.conversation_id, user_id):
            raise ValueError("User is not a participant in this conversation")

        # Update only the text content fields
        message.content_encrypted = content_encrypted
        message.content_hash = content_hash
        if settings.PQC_ENABLED:
            sender = db.query(User).filter(User.id == user_id).first()
            try:
                signature_created_at = datetime.now(timezone.utc)
                message.signature = CryptoService.sign_message(
                    sender,
                    message.conversation_id,
                    message.message_type,
                    content_encrypted,
                    signature_created_at,
                )
                message.signature_algorithm = "ML-DSA-65"
                message.signature_created_at = signature_created_at
            except (RuntimeError, ValueError):
                raise ValueError("Message authentication failed")
        message.is_edited = True
        message.edited_at = datetime.now(timezone.utc)

        # Update conversation's updated_at timestamp
        conversation = db.query(Conversation).filter(Conversation.id == message.conversation_id).first()
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
    def delete_message(
        db: Session,
        message_id: uuid.UUID,
        user_id: uuid.UUID,
        mode: str,
    ) -> Message:
        """
        Delete a message.

        Supports two modes:
        - "me": Hide the message only for the requesting user. The database
          row is preserved and other participants continue seeing the message.
        - "everyone": Soft-delete the message for all participants. The
          database row, message ID, reply relationships, attachment metadata,
          and audit trail are all preserved.

        Security model:
        - The user must be an active participant in the message's conversation.
        - "everyone" mode requires the user to be the original sender.
        - System messages cannot be deleted.
        - Already-deleted messages cannot be deleted again.
        - Cross-conversation requests are rejected (message ID must belong
          to a conversation the user is a participant of).

        Args:
            db: Database session
            message_id: UUID of the message to delete
            user_id: UUID of the user attempting the deletion
            mode: Deletion mode — "me" or "everyone"

        Returns:
            Message: The updated message object

        Raises:
            ValueError: If:
                - Message does not exist
                - Message is already deleted
                - Message is a system message
                - User is not an active participant in the conversation
                - Mode is "everyone" and user is not the original sender
                - Mode is invalid
        """
        # Validate mode
        if mode not in ("me", "everyone"):
            raise ValueError("Invalid delete mode. Must be 'me' or 'everyone'")

        # Load the message
        message = db.query(Message).filter(Message.id == message_id).first()
        if message is None:
            raise ValueError("Message not found")

        # Reject already-deleted messages
        if message.is_deleted:
            raise ValueError("Message is already deleted")

        # Reject system messages
        if message.message_type == "system":
            raise ValueError("Cannot delete a system message")

        # Conversation authorization — user must be an active participant
        if not is_participant(db, message.conversation_id, user_id):
            raise ValueError("User is not a participant in this conversation")

        # Ownership verification for "everyone" mode — only the sender can
        # delete for everyone
        if mode == "everyone" and message.sender_id != user_id:
            raise ValueError("You can only delete your own messages for everyone")

        # Apply the deletion
        now = datetime.now(timezone.utc)
        message.deleted_at = now
        message.deleted_by = user_id
        message.delete_type = mode

        if mode == "everyone":
            # Soft delete for all participants
            message.is_deleted = True

        # Update conversation's updated_at timestamp
        conversation = db.query(Conversation).filter(Conversation.id == message.conversation_id).first()
        if conversation:
            conversation.updated_at = now

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
    reply_to_message_id: Optional[uuid.UUID] = None,
    attachment_ids: Optional[list[uuid.UUID]] = None,
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
        reply_to_message_id=reply_to_message_id,
        attachment_ids=attachment_ids,
    )


def edit_message(
    db: Session,
    message_id: uuid.UUID,
    user_id: uuid.UUID,
    content_encrypted: str,
    content_hash: str,
) -> Message:
    """Convenience function to edit a message."""
    return MessageService.edit_message(
        db=db,
        message_id=message_id,
        user_id=user_id,
        content_encrypted=content_encrypted,
        content_hash=content_hash,
    )


def delete_message(
    db: Session,
    message_id: uuid.UUID,
    user_id: uuid.UUID,
    mode: str,
) -> Message:
    """Convenience function to delete a message."""
    return MessageService.delete_message(
        db=db,
        message_id=message_id,
        user_id=user_id,
        mode=mode,
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