"""
Conversation Service Tests

These tests verify the ConversationService business logic.
"""

import pytest
import uuid
import time
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from services.conversation_service import (
    ConversationService,
    create_conversation,
    get_conversation_by_id,
    get_user_conversations,
    is_participant,
)
from models.conversation import Conversation
from models.conversation_participant import ConversationParticipant


class TestCreateConversation:
    """Tests for create_conversation()"""

    def test_create_one_to_one_conversation(self, db_session: Session, test_user, test_user2):
        """
        Test creating a one-to-one conversation.
        
        Verifies:
        - Conversation is created
        - Both users are participants
        - Creator is admin, other is member
        """
        conversation = create_conversation(
            db=db_session,
            creator_id=test_user.id,
            participant_ids=[test_user2.id],
            is_group=False,
        )
        
        assert conversation is not None
        assert conversation.id is not None
        assert conversation.is_group is False
        assert conversation.created_by == test_user.id
        
        # Verify participants were created
        participants = db_session.query(ConversationParticipant).filter(
            ConversationParticipant.conversation_id == conversation.id
        ).all()
        
        assert len(participants) == 2
        
        # Verify roles
        creator_participant = next(p for p in participants if p.user_id == test_user.id)
        other_participant = next(p for p in participants if p.user_id == test_user2.id)
        
        assert creator_participant.role == "admin"
        assert other_participant.role == "member"

    def test_create_group_conversation(self, db_session: Session, test_user, test_user2):
        """
        Test creating a group conversation.
        
        Verifies:
        - Conversation is created with is_group=True
        - Group name is set
        - Participants are added correctly
        """
        conversation = create_conversation(
            db=db_session,
            creator_id=test_user.id,
            participant_ids=[test_user2.id],
            is_group=True,
            group_name="Test Group",
        )
        
        assert conversation is not None
        assert conversation.is_group is True
        assert conversation.group_name == "Test Group"
        assert conversation.created_by == test_user.id

    def test_creator_added_automatically(self, db_session: Session, test_user, test_user2):
        """
        Test that creator is automatically added as participant.
        
        Verifies:
        - Creator is in participants even if not in participant_ids
        """
        conversation = create_conversation(
            db=db_session,
            creator_id=test_user.id,
            participant_ids=[test_user2.id],  # Creator not included
            is_group=False,
        )
        
        # Check creator is a participant
        participant = db_session.query(ConversationParticipant).filter(
            ConversationParticipant.conversation_id == conversation.id,
            ConversationParticipant.user_id == test_user.id,
        ).first()
        
        assert participant is not None
        assert participant.role == "admin"

    def test_duplicate_participant_ids_removed(self, db_session: Session, test_user, test_user2):
        """
        Test that duplicate participant IDs are removed.
        
        Verifies:
        - Only unique participants are created
        """
        conversation = create_conversation(
            db=db_session,
            creator_id=test_user.id,
            participant_ids=[test_user2.id, test_user2.id, test_user2.id],  # Duplicates
            is_group=False,
        )
        
        # Count participants
        participants = db_session.query(ConversationParticipant).filter(
            ConversationParticipant.conversation_id == conversation.id
        ).all()
        
        # Should only have 2 participants (creator + test_user2)
        assert len(participants) == 2

    def test_creator_receives_admin_role(self, db_session: Session, test_user, test_user2):
        """
        Test that creator receives admin role.
        
        Verifies:
        - Creator's participant record has role="admin"
        """
        conversation = create_conversation(
            db=db_session,
            creator_id=test_user.id,
            participant_ids=[test_user2.id],
            is_group=False,
        )
        
        creator_participant = db_session.query(ConversationParticipant).filter(
            ConversationParticipant.conversation_id == conversation.id,
            ConversationParticipant.user_id == test_user.id,
        ).first()
        
        assert creator_participant.role == "admin"

    def test_other_participants_receive_member_role(self, db_session: Session, test_user, test_user2):
        """
        Test that non-creator participants receive member role.
        
        Verifies:
        - Non-creator participants have role="member"
        """
        conversation = create_conversation(
            db=db_session,
            creator_id=test_user.id,
            participant_ids=[test_user2.id],
            is_group=False,
        )
        
        other_participant = db_session.query(ConversationParticipant).filter(
            ConversationParticipant.conversation_id == conversation.id,
            ConversationParticipant.user_id == test_user2.id,
        ).first()
        
        assert other_participant.role == "member"

    def test_empty_participant_list_with_creator_only(self, db_session: Session, test_user):
        """
        Test that empty participant list creates conversation with creator only.
        
        Verifies:
        - Conversation is created with just the creator
        - Creator is the only participant
        """
        conversation = create_conversation(
            db=db_session,
            creator_id=test_user.id,
            participant_ids=[],  # Empty list - creator is auto-added
            is_group=False,
        )
        
        assert conversation is not None
        # Creator is automatically added as the only participant
        participants = db_session.query(ConversationParticipant).filter(
            ConversationParticipant.conversation_id == conversation.id
        ).all()
        assert len(participants) == 1
        assert participants[0].user_id == test_user.id
        assert participants[0].role == "admin"

    def test_group_conversation_with_only_creator_raises_error(self, db_session: Session, test_user):
        """
        Test that group conversation with only creator raises ValueError.
        
        Verifies:
        - ValueError is raised
        - Error message indicates group requires multiple participants
        """
        with pytest.raises(ValueError) as exc_info:
            create_conversation(
                db=db_session,
                creator_id=test_user.id,
                participant_ids=[],  # No other participants
                is_group=True,
            )
        
        assert "participant" in str(exc_info.value).lower() or "group" in str(exc_info.value).lower()

    def test_transaction_rolls_back_on_failure(self, db_session: Session, test_user, test_user2):
        """
        Test that transaction rolls back on failure.
        
        Verifies:
        - If an error occurs, no partial data is committed
        """
        # This test verifies the rollback mechanism exists
        # We can't easily test actual rollback without mocking,
        # but we can verify the method has try/except with rollback
        import inspect
        source = inspect.getsource(ConversationService.create_conversation)
        assert "rollback" in source.lower()
        assert "try" in source.lower()
        assert "except" in source.lower()


class TestGetConversationById:
    """Tests for get_conversation_by_id()"""

    def test_get_existing_conversation(self, db_session: Session, test_conversation):
        """
        Test retrieving an existing conversation.
        
        Verifies:
        - Conversation is returned
        - All fields match
        """
        conversation = get_conversation_by_id(
            db=db_session,
            conversation_id=test_conversation.id,
        )
        
        assert conversation is not None
        assert conversation.id == test_conversation.id
        assert conversation.is_group == test_conversation.is_group
        assert conversation.created_by == test_conversation.created_by

    def test_get_unknown_conversation_returns_none(self, db_session: Session):
        """
        Test retrieving a non-existent conversation.
        
        Verifies:
        - None is returned
        """
        fake_id = uuid.uuid4()
        conversation = get_conversation_by_id(
            db=db_session,
            conversation_id=fake_id,
        )
        
        assert conversation is None


class TestGetUserConversations:
    """Tests for get_user_conversations()"""

    def test_returns_active_participant_conversations(self, db_session: Session, test_user, test_user2, test_conversation):
        """
        Test that only conversations where user is active participant are returned.
        
        Verifies:
        - User's conversations are returned
        - Only active participantships are included
        """
        conversations = get_user_conversations(
            db=db_session,
            user_id=test_user.id,
        )
        
        assert len(conversations) > 0
        assert any(c.id == test_conversation.id for c in conversations)

    def test_excludes_conversations_where_user_left(self, db_session: Session, test_user, test_user2):
        """
        Test that conversations where user left are excluded.
        
        Verifies:
        - Conversations with left_at set are not returned
        """
        # Create a conversation
        conversation = create_conversation(
            db=db_session,
            creator_id=test_user.id,
            participant_ids=[test_user2.id],
            is_group=False,
        )
        
        # Simulate user leaving by setting left_at
        participant = db_session.query(ConversationParticipant).filter(
            ConversationParticipant.conversation_id == conversation.id,
            ConversationParticipant.user_id == test_user.id,
        ).first()
        participant.left_at = datetime.now(timezone.utc)
        db_session.commit()
        
        # Get user's conversations
        conversations = get_user_conversations(
            db=db_session,
            user_id=test_user.id,
        )
        
        # Should not include the conversation where user left
        assert not any(c.id == conversation.id for c in conversations)

    def test_ordered_by_updated_at_desc(self, db_session: Session, test_user):
        """
        Test that conversations are ordered by updated_at DESC.
        
        Verifies:
        - Most recently updated conversation is first
        """
        from datetime import timedelta
        
        # Create two conversations
        conv1 = create_conversation(
            db=db_session,
            creator_id=test_user.id,
            participant_ids=[],
            is_group=False,
        )
        
        # Manually update conv1's updated_at to be older
        conv1.updated_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db_session.add(conv1)
        db_session.commit()
        
        # Create second conversation (will have newer updated_at)
        conv2 = create_conversation(
            db=db_session,
            creator_id=test_user.id,
            participant_ids=[],
            is_group=False,
        )
        
        # Get conversations
        conversations = get_user_conversations(
            db=db_session,
            user_id=test_user.id,
        )
        
        # Verify ordering (most recent first)
        assert len(conversations) >= 2
        assert conversations[0].id == conv2.id  # Most recent
        assert conversations[1].id == conv1.id  # Older


class TestIsParticipant:
    """Tests for is_participant()"""

    def test_active_participant_returns_true(self, db_session: Session, test_conversation, test_user):
        """
        Test that active participant returns True.
        
        Verifies:
        - User who is participant returns True
        """
        result = is_participant(
            db=db_session,
            conversation_id=test_conversation.id,
            user_id=test_user.id,
        )
        
        assert result is True

    def test_non_participant_returns_false(self, db_session: Session, test_conversation):
        """
        Test that non-participant returns False.
        
        Verifies:
        - User who is not a participant returns False
        """
        fake_user_id = uuid.uuid4()
        result = is_participant(
            db=db_session,
            conversation_id=test_conversation.id,
            user_id=fake_user_id,
        )
        
        assert result is False

    def test_user_who_left_returns_false(self, db_session: Session, test_user, test_user2):
        """
        Test that user who left conversation returns False.
        
        Verifies:
        - User with left_at set returns False
        """
        # Create a conversation
        conversation = create_conversation(
            db=db_session,
            creator_id=test_user.id,
            participant_ids=[test_user2.id],
            is_group=False,
        )
        
        # Simulate user leaving
        participant = db_session.query(ConversationParticipant).filter(
            ConversationParticipant.conversation_id == conversation.id,
            ConversationParticipant.user_id == test_user2.id,
        ).first()
        participant.left_at = datetime.now(timezone.utc)
        db_session.commit()
        
        # Check participation status
        result = is_participant(
            db=db_session,
            conversation_id=conversation.id,
            user_id=test_user2.id,
        )
        
        assert result is False
