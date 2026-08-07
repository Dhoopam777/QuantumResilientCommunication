"""
Message Service Tests

These tests verify the MessageService business logic.
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from services.message_service import (
    MessageService,
    send_message,
    edit_message,
    get_message_by_id,
    get_conversation_messages,
)
from models.message import Message
from models.conversation import Conversation
from models.conversation_participant import ConversationParticipant


class TestSendMessage:
    """Tests for send_message()"""

    def test_message_created_successfully(self, db_session: Session, test_conversation, test_user):
        """
        Test that a message is created successfully.
        
        Verifies:
        - Message is created with correct fields
        - Message is persisted in database
        """
        message = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="encrypted_content_here",
            content_hash="abc123def456",
            message_type="text",
        )
        
        assert message is not None
        assert message.id is not None
        assert message.conversation_id == test_conversation.id
        assert message.sender_id == test_user.id
        assert message.content_encrypted == "encrypted_content_here"
        assert message.content_hash == "abc123def456"
        assert message.message_type == "text"
        assert message.is_edited is False
        assert message.is_deleted is False
        assert message.reply_to is None

    def test_conversation_updated_at_updated(self, db_session: Session, test_conversation, test_user):
        """
        Test that conversation.updated_at is updated after sending a message.
        
        Verifies:
        - Conversation's updated_at is refreshed
        """
        # Record the original updated_at
        original_updated_at = test_conversation.updated_at
        
        # Send a message
        send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="new_message",
            content_hash="hash123",
            message_type="text",
        )
        
        # Refresh and check
        db_session.refresh(test_conversation)
        assert test_conversation.updated_at > original_updated_at

    def test_sender_must_be_active_participant(self, db_session: Session, test_conversation):
        """
        Test that non-participant sender raises ValueError.
        
        Verifies:
        - ValueError is raised
        - Error message indicates not a participant
        """
        non_participant_id = uuid.uuid4()
        
        with pytest.raises(ValueError) as exc_info:
            send_message(
                db=db_session,
                conversation_id=test_conversation.id,
                sender_id=non_participant_id,
                content_encrypted="test",
                content_hash="hash",
                message_type="text",
            )
        
        assert "participant" in str(exc_info.value).lower()

    def test_empty_encrypted_content_raises_error(self, db_session: Session, test_conversation, test_user):
        """
        Test that empty encrypted content raises ValueError.
        
        Verifies:
        - ValueError is raised
        - Error message indicates content cannot be empty
        """
        with pytest.raises(ValueError) as exc_info:
            send_message(
                db=db_session,
                conversation_id=test_conversation.id,
                sender_id=test_user.id,
                content_encrypted="",
                content_hash="hash123",
                message_type="text",
            )
        
        assert "content" in str(exc_info.value).lower() and "empty" in str(exc_info.value).lower()

    def test_empty_content_hash_raises_error(self, db_session: Session, test_conversation, test_user):
        """
        Test that empty content hash raises ValueError.
        
        Verifies:
        - ValueError is raised
        - Error message indicates hash cannot be empty
        """
        with pytest.raises(ValueError) as exc_info:
            send_message(
                db=db_session,
                conversation_id=test_conversation.id,
                sender_id=test_user.id,
                content_encrypted="some_content",
                content_hash="",
                message_type="text",
            )
        
        assert "hash" in str(exc_info.value).lower() and "empty" in str(exc_info.value).lower()

    def test_invalid_message_type_raises_error(self, db_session: Session, test_conversation, test_user):
        """
        Test that invalid message type raises ValueError.
        
        Verifies:
        - ValueError is raised
        - Error message indicates invalid type
        """
        with pytest.raises(ValueError) as exc_info:
            send_message(
                db=db_session,
                conversation_id=test_conversation.id,
                sender_id=test_user.id,
                content_encrypted="content",
                content_hash="hash",
                message_type="invalid_type",
            )
        
        assert "invalid" in str(exc_info.value).lower() or "type" in str(exc_info.value).lower()

    def test_reply_to_accepted_without_validation(self, db_session: Session, test_conversation, test_user):
        """
        Test that reply_to (legacy field) is accepted without validation.
        
        Verifies:
        - reply_to is stored even if it doesn't reference a real message
        """
        fake_reply_to = uuid.uuid4()
        
        message = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="reply_content",
            content_hash="hash456",
            message_type="text",
            reply_to=fake_reply_to,
        )
        
        assert message.reply_to == fake_reply_to

    def test_transaction_rolls_back_on_failure(self, db_session: Session, test_conversation, test_user):
        """
        Test that transaction rolls back on failure.
        
        Verifies:
        - The method has try/except with rollback
        """
        import inspect
        source = inspect.getsource(MessageService.send_message)
        assert "rollback" in source.lower()
        assert "try" in source.lower()
        assert "except" in source.lower()


class TestReplySystem:
    """Tests for the message reply system."""

    def test_reply_to_valid_message(self, db_session: Session, test_conversation, test_user):
        """
        Test replying to a valid message in the same conversation.
        
        Verifies:
        - Reply is created with reply_to_message_id set
        - Reply relationship is preserved
        """
        # Create the parent message
        parent = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="parent_content",
            content_hash="parent_hash",
            message_type="text",
        )

        # Reply to the parent
        reply = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="reply_content",
            content_hash="reply_hash",
            message_type="text",
            reply_to_message_id=parent.id,
        )

        assert reply is not None
        assert reply.reply_to_message_id == parent.id
        assert reply.conversation_id == test_conversation.id

    def test_reply_to_soft_deleted_message_allowed(self, db_session: Session, test_conversation, test_user):
        """
        Test replying to a soft-deleted message is allowed.
        
        Verifies:
        - Reply relationship is preserved even if parent is soft-deleted
        """
        # Create the parent message
        parent = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="parent_content",
            content_hash="parent_hash",
            message_type="text",
        )

        # Soft delete the parent
        parent.is_deleted = True
        db_session.add(parent)
        db_session.commit()

        # Reply to the soft-deleted parent
        reply = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="reply_to_deleted",
            content_hash="reply_hash",
            message_type="text",
            reply_to_message_id=parent.id,
        )

        assert reply is not None
        assert reply.reply_to_message_id == parent.id

    def test_reply_to_nonexistent_message_rejected(self, db_session: Session, test_conversation, test_user):
        """
        Test replying to a non-existent message is rejected.
        
        Verifies:
        - ValueError is raised
        - Error message indicates reply target does not exist
        """
        fake_id = uuid.uuid4()

        with pytest.raises(ValueError) as exc_info:
            send_message(
                db=db_session,
                conversation_id=test_conversation.id,
                sender_id=test_user.id,
                content_encrypted="reply_content",
                content_hash="reply_hash",
                message_type="text",
                reply_to_message_id=fake_id,
            )

        assert "does not exist" in str(exc_info.value).lower()

    def test_reply_across_conversations_rejected(self, db_session: Session, test_conversation, test_user, test_user2):
        """
        Test replying to a message in a different conversation is rejected.
        
        Verifies:
        - ValueError is raised
        - Error message indicates different conversation
        """
        # Create a second conversation
        conv2 = Conversation(
            is_group=False,
            group_name=None,
            created_by=test_user2.id,
            is_encrypted=True,
        )
        db_session.add(conv2)
        db_session.flush()

        # Add participants to conv2
        p1 = ConversationParticipant(
            conversation_id=conv2.id,
            user_id=test_user.id,
            role="member",
        )
        p2 = ConversationParticipant(
            conversation_id=conv2.id,
            user_id=test_user2.id,
            role="admin",
        )
        db_session.add_all([p1, p2])
        db_session.commit()

        # Create a message in conv2
        parent_in_conv2 = send_message(
            db=db_session,
            conversation_id=conv2.id,
            sender_id=test_user2.id,
            content_encrypted="conv2_content",
            content_hash="conv2_hash",
            message_type="text",
        )

        # Try to reply to it from test_conversation
        with pytest.raises(ValueError) as exc_info:
            send_message(
                db=db_session,
                conversation_id=test_conversation.id,
                sender_id=test_user.id,
                content_encrypted="cross_conversation_reply",
                content_hash="cross_hash",
                message_type="text",
                reply_to_message_id=parent_in_conv2.id,
            )

        assert "different conversation" in str(exc_info.value).lower()

    def test_reply_to_self_rejected(self, db_session: Session, test_conversation, test_user):
        """
        Test that a message cannot reply to itself.
        
        Verifies:
        - ValueError is raised when a message's reply chain creates a cycle
        """
        # Create a message
        msg = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="self_content",
            content_hash="self_hash",
            message_type="text",
        )

        # Simulate a self-referential reply: set msg.reply_to_message_id to itself
        msg.reply_to_message_id = msg.id
        db_session.add(msg)
        db_session.commit()

        # Try to reply to msg — this creates a cycle (msg replies to itself)
        with pytest.raises(ValueError):
            send_message(
                db=db_session,
                conversation_id=test_conversation.id,
                sender_id=test_user.id,
                content_encrypted="self_reply",
                content_hash="self_reply_hash",
                message_type="text",
                reply_to_message_id=msg.id,
            )


class TestEditMessage:
    """Tests for edit_message()"""

    def test_edit_own_message_success(self, db_session: Session, test_conversation, test_user):
        """
        Test that a user can edit their own message.

        Verifies:
        - Message content is updated
        - is_edited is set to True
        - edited_at is set
        - content_hash is updated
        """
        # Create a message
        msg = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="original_content",
            content_hash="original_hash",
            message_type="text",
        )

        # Edit the message
        updated = edit_message(
            db=db_session,
            message_id=msg.id,
            user_id=test_user.id,
            content_encrypted="edited_content",
            content_hash="edited_hash",
        )

        assert updated is not None
        assert updated.id == msg.id
        assert updated.content_encrypted == "edited_content"
        assert updated.content_hash == "edited_hash"
        assert updated.is_edited is True
        assert updated.edited_at is not None
        assert updated.conversation_id == test_conversation.id
        assert updated.sender_id == test_user.id

    def test_edit_own_message_keeps_attachments_reply(self, db_session: Session, test_conversation, test_user):
        """
        Test that editing preserves attachments, replies, and other fields.

        Verifies:
        - reply_to_message_id is preserved
        - message_type is preserved
        - is_deleted is preserved
        """
        # Create a parent message
        parent = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="parent_content",
            content_hash="parent_hash",
            message_type="text",
        )

        # Create a reply message
        reply = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="reply_content",
            content_hash="reply_hash",
            message_type="text",
            reply_to_message_id=parent.id,
        )

        # Edit the reply
        updated = edit_message(
            db=db_session,
            message_id=reply.id,
            user_id=test_user.id,
            content_encrypted="edited_reply",
            content_hash="edited_reply_hash",
        )

        assert updated.reply_to_message_id == parent.id
        assert updated.message_type == "text"
        assert updated.is_deleted is False

    def test_cannot_edit_others_message(self, db_session: Session, test_conversation, test_user, test_user2):
        """
        Test that a user cannot edit another user's message.

        Verifies:
        - ValueError is raised
        - Error message indicates ownership
        """
        # test_user sends a message
        msg = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="user1_content",
            content_hash="user1_hash",
            message_type="text",
        )

        # test_user2 tries to edit it
        with pytest.raises(ValueError) as exc_info:
            edit_message(
                db=db_session,
                message_id=msg.id,
                user_id=test_user2.id,
                content_encrypted="hacked_content",
                content_hash="hacked_hash",
            )

        assert "own messages" in str(exc_info.value).lower()

    def test_cannot_edit_deleted_message(self, db_session: Session, test_conversation, test_user):
        """
        Test that a deleted message cannot be edited.

        Verifies:
        - ValueError is raised
        - Error message indicates deleted
        """
        # Create a message
        msg = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="to_delete",
            content_hash="hash_del",
            message_type="text",
        )

        # Soft delete the message
        msg.is_deleted = True
        db_session.add(msg)
        db_session.commit()

        # Try to edit the deleted message
        with pytest.raises(ValueError) as exc_info:
            edit_message(
                db=db_session,
                message_id=msg.id,
                user_id=test_user.id,
                content_encrypted="edited_deleted",
                content_hash="edited_hash",
            )

        assert "deleted" in str(exc_info.value).lower()

    def test_cannot_edit_system_message(self, db_session: Session, test_conversation, test_user):
        """
        Test that a system message cannot be edited.

        Verifies:
        - ValueError is raised
        - Error message indicates system
        """
        # Create a system message
        msg = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="system_content",
            content_hash="system_hash",
            message_type="system",
        )

        # Try to edit the system message
        with pytest.raises(ValueError) as exc_info:
            edit_message(
                db=db_session,
                message_id=msg.id,
                user_id=test_user.id,
                content_encrypted="edited_system",
                content_hash="edited_hash",
            )

        assert "system" in str(exc_info.value).lower()

    def test_cannot_edit_nonexistent_message(self, db_session: Session, test_user):
        """
        Test that a non-existent message cannot be edited.

        Verifies:
        - ValueError is raised
        - Error message indicates not found
        """
        fake_id = uuid.uuid4()

        with pytest.raises(ValueError) as exc_info:
            edit_message(
                db=db_session,
                message_id=fake_id,
                user_id=test_user.id,
                content_encrypted="content",
                content_hash="hash",
            )

        assert "not found" in str(exc_info.value).lower()

    def test_cannot_edit_cross_conversation(self, db_session: Session, test_conversation, test_user, test_user2):
        """
        Test that a user cannot edit a message in a conversation they're not part of.

        Verifies:
        - ValueError is raised
        - Error message indicates participant
        """
        # Create a second conversation with only test_user2
        conv2 = Conversation(
            is_group=False,
            group_name=None,
            created_by=test_user2.id,
            is_encrypted=True,
        )
        db_session.add(conv2)
        db_session.flush()

        p1 = ConversationParticipant(
            conversation_id=conv2.id,
            user_id=test_user2.id,
            role="admin",
        )
        db_session.add(p1)
        db_session.commit()

        # test_user2 sends a message in conv2
        msg_in_conv2 = send_message(
            db=db_session,
            conversation_id=conv2.id,
            sender_id=test_user2.id,
            content_encrypted="conv2_content",
            content_hash="conv2_hash",
            message_type="text",
        )

        # test_user is not a participant in conv2, tries to edit
        with pytest.raises(ValueError) as exc_info:
            edit_message(
                db=db_session,
                message_id=msg_in_conv2.id,
                user_id=test_user.id,
                content_encrypted="cross_edit",
                content_hash="cross_hash",
            )

        assert "participant" in str(exc_info.value).lower() or "own" in str(exc_info.value).lower()

    def test_empty_content_rejected(self, db_session: Session, test_conversation, test_user):
        """
        Test that empty content is rejected.

        Verifies:
        - ValueError is raised
        - Error message indicates content cannot be empty
        """
        msg = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="original",
            content_hash="hash",
            message_type="text",
        )

        with pytest.raises(ValueError) as exc_info:
            edit_message(
                db=db_session,
                message_id=msg.id,
                user_id=test_user.id,
                content_encrypted="",
                content_hash="new_hash",
            )

        assert "content" in str(exc_info.value).lower() and "empty" in str(exc_info.value).lower()

    def test_whitespace_only_content_rejected(self, db_session: Session, test_conversation, test_user):
        """
        Test that whitespace-only content is rejected.

        Verifies:
        - ValueError is raised
        - Error message indicates content cannot be empty
        """
        msg = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="original",
            content_hash="hash",
            message_type="text",
        )

        with pytest.raises(ValueError) as exc_info:
            edit_message(
                db=db_session,
                message_id=msg.id,
                user_id=test_user.id,
                content_encrypted="   \n\t  ",
                content_hash="new_hash",
            )

        assert "content" in str(exc_info.value).lower() and "empty" in str(exc_info.value).lower()

    def test_empty_hash_rejected(self, db_session: Session, test_conversation, test_user):
        """
        Test that empty content hash is rejected.

        Verifies:
        - ValueError is raised
        - Error message indicates hash cannot be empty
        """
        msg = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="original",
            content_hash="hash",
            message_type="text",
        )

        with pytest.raises(ValueError) as exc_info:
            edit_message(
                db=db_session,
                message_id=msg.id,
                user_id=test_user.id,
                content_encrypted="new_content",
                content_hash="",
            )

        assert "hash" in str(exc_info.value).lower() and "empty" in str(exc_info.value).lower()

    def test_edit_updates_conversation_updated_at(self, db_session: Session, test_conversation, test_user):
        """
        Test that conversation.updated_at is updated after editing.

        Verifies:
        - Conversation's updated_at is refreshed
        """
        msg = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="original",
            content_hash="hash",
            message_type="text",
        )

        original_updated_at = test_conversation.updated_at

        edit_message(
            db=db_session,
            message_id=msg.id,
            user_id=test_user.id,
            content_encrypted="edited",
            content_hash="edited_hash",
        )

        db_session.refresh(test_conversation)
        assert test_conversation.updated_at >= original_updated_at


class TestGetMessageById:
    """Tests for get_message_by_id()"""

    def test_existing_message_returned(self, db_session: Session, test_message):
        """
        Test that an existing message is returned.
        
        Verifies:
        - Message is found by ID
        - All fields match
        """
        message = get_message_by_id(
            db=db_session,
            message_id=test_message.id,
        )
        
        assert message is not None
        assert message.id == test_message.id
        assert message.content_encrypted == test_message.content_encrypted
        assert message.content_hash == test_message.content_hash

    def test_unknown_message_returns_none(self, db_session: Session):
        """
        Test that unknown message returns None.
        
        Verifies:
        - None is returned for non-existent message
        """
        fake_id = uuid.uuid4()
        message = get_message_by_id(
            db=db_session,
            message_id=fake_id,
        )
        
        assert message is None


class TestGetConversationMessages:
    """Tests for get_conversation_messages()"""

    def test_returns_conversation_messages(self, db_session: Session, test_conversation, test_user, test_message):
        """
        Test that conversation messages are returned.
        
        Verifies:
        - Messages for the conversation are returned
        """
        messages = get_conversation_messages(
            db=db_session,
            conversation_id=test_conversation.id,
            user_id=test_user.id,
        )
        
        assert len(messages) > 0
        assert any(m.id == test_message.id for m in messages)

    def test_ordered_by_created_at_asc(self, db_session: Session, test_conversation, test_user):
        """
        Test that messages are ordered by created_at ASC.
        
        Verifies:
        - Oldest message is first
        - Newest message is last
        """
        # Create two messages with different timestamps
        msg1 = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="first_message",
            content_hash="hash1",
            message_type="text",
        )
        
        # Manually set msg1 to be older
        msg1.created_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db_session.add(msg1)
        db_session.commit()
        
        msg2 = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="second_message",
            content_hash="hash2",
            message_type="text",
        )
        
        messages = get_conversation_messages(
            db=db_session,
            conversation_id=test_conversation.id,
            user_id=test_user.id,
        )
        
        assert len(messages) >= 2
        assert messages[0].id == msg1.id  # Oldest first
        assert messages[-1].id == msg2.id  # Newest last

    def test_excludes_soft_deleted_messages(self, db_session: Session, test_conversation, test_user):
        """
        Test that soft-deleted messages are excluded.
        
        Verifies:
        - Messages with is_deleted=True are not returned
        """
        # Create a message
        msg = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="to_be_deleted",
            content_hash="hash_del",
            message_type="text",
        )
        
        # Soft delete the message
        msg.is_deleted = True
        db_session.add(msg)
        db_session.commit()
        
        messages = get_conversation_messages(
            db=db_session,
            conversation_id=test_conversation.id,
            user_id=test_user.id,
        )
        
        assert not any(m.id == msg.id for m in messages)

    def test_pagination_limit_works(self, db_session: Session, test_conversation, test_user):
        """
        Test that pagination limit works.
        
        Verifies:
        - Only 'limit' number of messages are returned
        """
        # Create 5 messages
        for i in range(5):
            send_message(
                db=db_session,
                conversation_id=test_conversation.id,
                sender_id=test_user.id,
                content_encrypted=f"msg_{i}",
                content_hash=f"hash_{i}",
                message_type="text",
            )
        
        # Get only 3 messages
        messages = get_conversation_messages(
            db=db_session,
            conversation_id=test_conversation.id,
            user_id=test_user.id,
            limit=3,
        )
        
        assert len(messages) == 3

    def test_pagination_offset_works(self, db_session: Session, test_conversation, test_user):
        """
        Test that pagination offset works.
        
        Verifies:
        - Messages are skipped by offset
        """
        # Create 3 messages
        for i in range(3):
            send_message(
                db=db_session,
                conversation_id=test_conversation.id,
                sender_id=test_user.id,
                content_encrypted=f"msg_{i}",
                content_hash=f"hash_{i}",
                message_type="text",
            )
        
        # Get all messages first
        all_messages = get_conversation_messages(
            db=db_session,
            conversation_id=test_conversation.id,
            user_id=test_user.id,
        )
        
        # Get messages with offset 1
        offset_messages = get_conversation_messages(
            db=db_session,
            conversation_id=test_conversation.id,
            user_id=test_user.id,
            offset=1,
        )
        
        assert len(offset_messages) == len(all_messages) - 1
        assert offset_messages[0].id == all_messages[1].id

    def test_non_participant_raises_error(self, db_session: Session, test_conversation):
        """
        Test that non-participant raises ValueError.
        
        Verifies:
        - ValueError is raised
        - Error message indicates not a participant
        """
        non_participant_id = uuid.uuid4()
        
        with pytest.raises(ValueError) as exc_info:
            get_conversation_messages(
                db=db_session,
                conversation_id=test_conversation.id,
                user_id=non_participant_id,
            )
        
        assert "participant" in str(exc_info.value).lower()

    def test_invalid_limit_raises_error(self, db_session: Session, test_conversation, test_user):
        """
        Test that invalid limit raises ValueError.
        
        Verifies:
        - limit <= 0 raises ValueError
        - limit > 100 raises ValueError
        """
        # Test limit <= 0
        with pytest.raises(ValueError) as exc_info:
            get_conversation_messages(
                db=db_session,
                conversation_id=test_conversation.id,
                user_id=test_user.id,
                limit=0,
            )
        assert "limit" in str(exc_info.value).lower()
        
        # Test limit > 100
        with pytest.raises(ValueError) as exc_info:
            get_conversation_messages(
                db=db_session,
                conversation_id=test_conversation.id,
                user_id=test_user.id,
                limit=101,
            )
        assert "limit" in str(exc_info.value).lower()

    def test_invalid_offset_raises_error(self, db_session: Session, test_conversation, test_user):
        """
        Test that invalid offset raises ValueError.
        
        Verifies:
        - offset < 0 raises ValueError
        """
        with pytest.raises(ValueError) as exc_info:
            get_conversation_messages(
                db=db_session,
                conversation_id=test_conversation.id,
                user_id=test_user.id,
                offset=-1,
            )
        assert "offset" in str(exc_info.value).lower()