"""
Conversation Service for Quantum-Resilient Communication System

This module provides business logic for conversation operations.
"""

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from models.conversation import Conversation
from models.conversation_participant import ConversationParticipant
from models.message import Message
from models.user import User
from sqlalchemy import desc


class ConversationService:
    """Service class for conversation-related operations."""

    @staticmethod
    def create_conversation(
        db: Session,
        creator_id: uuid.UUID,
        participant_ids: list[uuid.UUID],
        is_group: bool = False,
        group_name: Optional[str] = None,
    ) -> Conversation:
        """
        Create a new conversation with participants.

        Automatically includes the creator as a participant if not already present.
        Deduplicates participant IDs automatically.
        Creator receives role="admin", other participants receive role="member".

        Args:
            db: Database session
            creator_id: UUID of the user creating the conversation
            participant_ids: List of user UUIDs to include as participants
            is_group: Whether this is a group conversation (default: False)
            group_name: Name for group conversations (optional)

        Returns:
            Conversation: The created conversation object

        Raises:
            ValueError: If participant list is empty after dedup/creator inclusion
        """
        # Build a set of all participant IDs (deduplicates automatically)
        all_participant_ids = set(participant_ids)

        # Ensure creator is included
        all_participant_ids.add(creator_id)

        # Validate there is at least one participant
        if not all_participant_ids:
            raise ValueError("Conversation must have at least one participant")

        # For group conversations, require more than just the creator
        if is_group and len(all_participant_ids) < 2:
            raise ValueError("Group conversation must have at least 2 participants")

        # Create the conversation
        conversation = Conversation(
            is_group=is_group,
            group_name=group_name if is_group else None,
            created_by=creator_id,
        )
        db.add(conversation)
        db.flush()  # Flush to get the conversation ID

        # Create participant records
        for user_id in all_participant_ids:
            role = "admin" if user_id == creator_id else "member"
            participant = ConversationParticipant(
                conversation_id=conversation.id,
                user_id=user_id,
                role=role,
            )
            db.add(participant)

        # Commit the transaction
        try:
            db.commit()
            db.refresh(conversation)
            return conversation
        except Exception:
            db.rollback()
            raise


    @staticmethod
    def get_conversation_by_id(db: Session, conversation_id: uuid.UUID) -> Optional[Conversation]:
        """
        Retrieve a conversation by its ID.

        Args:
            db: Database session
            conversation_id: UUID of the conversation

        Returns:
            Conversation object if found, None otherwise
        """
        return db.query(Conversation).filter(Conversation.id == conversation_id).first()

    @staticmethod
    def get_user_conversations(db: Session, user_id: uuid.UUID) -> list[Conversation]:
        """
        Retrieve all active conversations for a user.

        Returns conversations where the user is an active participant (left_at IS NULL),
        ordered by most recently updated first.

        Args:
            db: Database session
            user_id: UUID of the user

        Returns:
            List of Conversation objects ordered by updated_at DESC
        """
        return (
            db.query(Conversation)
            .join(ConversationParticipant, Conversation.id == ConversationParticipant.conversation_id)
            .filter(
                ConversationParticipant.user_id == user_id,
                ConversationParticipant.left_at.is_(None),
            )
            .order_by(desc(Conversation.updated_at))
            .all()
        )

    @staticmethod
    def is_participant(db: Session, conversation_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """
        Check if a user is an active participant in a conversation.

        Args:
            db: Database session
            conversation_id: UUID of the conversation
            user_id: UUID of the user

        Returns:
            True if the user is an active participant, False otherwise
        """
        return (
            db.query(ConversationParticipant)
            .filter(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id,
                ConversationParticipant.left_at.is_(None),
            )
            .first()
        ) is not None

    @staticmethod
    def get_conversation_participants(
        db: Session, conversation_id: uuid.UUID
    ) -> list[tuple[ConversationParticipant, User]]:
        """
        Retrieve all active participants with their user profile info for a conversation.

        Args:
            db: Database session
            conversation_id: UUID of the conversation

        Returns:
            List of (ConversationParticipant, User) tuples for active participants
        """
        return (
            db.query(ConversationParticipant, User)
            .join(User, ConversationParticipant.user_id == User.id)
            .filter(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.left_at.is_(None),
            )
            .all()
        )

    @staticmethod
    def get_last_message(db: Session, conversation_id: uuid.UUID) -> Optional[Message]:
        """
        Retrieve the most recent non-deleted message in a conversation.

        Args:
            db: Database session
            conversation_id: UUID of the conversation

        Returns:
            Message object if found, None otherwise
        """
        return (
            db.query(Message)
            .filter(
                Message.conversation_id == conversation_id,
                Message.is_deleted.is_(False),
            )
            .order_by(desc(Message.created_at))
            .first()
        )


# Convenience functions for direct usage
def create_conversation(
    db: Session,
    creator_id: uuid.UUID,
    participant_ids: list[uuid.UUID],
    is_group: bool = False,
    group_name: Optional[str] = None,
) -> Conversation:
    """Convenience function to create a new conversation."""
    return ConversationService.create_conversation(
        db=db,
        creator_id=creator_id,
        participant_ids=participant_ids,
        is_group=is_group,
        group_name=group_name,
    )


def get_conversation_by_id(db: Session, conversation_id: uuid.UUID) -> Optional[Conversation]:
    """Convenience function to get a conversation by ID."""
    return ConversationService.get_conversation_by_id(db, conversation_id)


def get_user_conversations(db: Session, user_id: uuid.UUID) -> list[Conversation]:
    """Convenience function to get all active conversations for a user."""
    return ConversationService.get_user_conversations(db, user_id)


def is_participant(db: Session, conversation_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """Convenience function to check if a user is an active participant."""
    return ConversationService.is_participant(db, conversation_id, user_id)


def get_conversation_participants(
    db: Session, conversation_id: uuid.UUID
) -> list[tuple]:
    """Convenience function to get conversation participants with user info."""
    return ConversationService.get_conversation_participants(db, conversation_id)


def get_last_message(db: Session, conversation_id: uuid.UUID) -> Optional[Message]:
    """Convenience function to get the last message in a conversation."""
    return ConversationService.get_last_message(db, conversation_id)
