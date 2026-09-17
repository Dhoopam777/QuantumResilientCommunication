"""
Message Deletion Service Tests

These tests verify the delete_message() business logic for both
"me" (Delete for Me) and "everyone" (Delete for Everyone) modes.
"""

import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from services.message_service import (
    send_message,
    delete_message,
    get_message_by_id,
    get_conversation_messages,
)
from models.message import Message
from models.conversation import Conversation
from models.conversation_participant import ConversationParticipant

from tests.pqc_helpers import install_signing_service_calls


@pytest.fixture(autouse=True)
def _client_signs_messages(db_session, monkeypatch):
    # Model a real client: outgoing messages carry device-produced signatures.
    # These tests exercise message CRUD behaviour, not signing, so the client
    # signature is supplied automatically, exactly as a real device would.
    install_signing_service_calls(db_session, monkeypatch, globals())



class TestDeleteMessageForMe:
    """Tests for delete_message() with mode='me'."""

    def test_delete_for_me_success(self, db_session: Session, test_conversation, test_user):
        """
        Test that 'delete for me' succeeds and marks deletion metadata.

        Verifies:
        - deleted_at is set
        - deleted_by is set to the requesting user
        - delete_type is 'me'
        - is_deleted remains False (other participants still see it)
        - Row is preserved (not removed from database)
        """
        msg = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="secret_content",
            content_hash="hash_me",
            message_type="text",
        )

        deleted = delete_message(
            db=db_session,
            message_id=msg.id,
            user_id=test_user.id,
            mode="me",
        )

        assert deleted is not None
        assert deleted.id == msg.id
        assert deleted.deleted_at is not None
        assert deleted.deleted_by == test_user.id
        assert deleted.delete_type == "me"
        # is_deleted must remain False — other participants see the message
        assert deleted.is_deleted is False
        # Row preserved
        assert db_session.query(Message).filter(Message.id == msg.id).first() is not None

    def test_delete_for_me_preserves_reply_relationship(
        self, db_session: Session, test_conversation, test_user
    ):
        """
        Test that deleting for me preserves reply relationships.

        Verifies:
        - reply_to_message_id is unchanged
        """
        parent = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="parent",
            content_hash="hash_p",
            message_type="text",
        )
        child = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="child",
            content_hash="hash_c",
            message_type="text",
            reply_to_message_id=parent.id,
        )

        delete_message(
            db=db_session,
            message_id=child.id,
            user_id=test_user.id,
            mode="me",
        )

        db_session.refresh(child)
        assert child.reply_to_message_id == parent.id
        assert child.deleted_at is not None
        assert child.delete_type == "me"

    def test_delete_for_me_other_users_still_see(
        self, db_session: Session, test_conversation, test_user, test_user2
    ):
        """
        Test that 'delete for me' does not affect other users' view.
        The message is still returned for other participants.
        """
        msg = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="shared_content",
            content_hash="hash_shared",
            message_type="text",
        )

        # test_user deletes for me
        delete_message(
            db=db_session,
            message_id=msg.id,
            user_id=test_user.id,
            mode="me",
        )

        # test_user2 still sees the message (is_deleted is False)
        db_session.refresh(msg)
        assert msg.is_deleted is False

        messages_for_user2 = get_conversation_messages(
            db=db_session,
            conversation_id=test_conversation.id,
            user_id=test_user2.id,
        )
        assert any(m.id == msg.id for m in messages_for_user2)


class TestDeleteMessageForEveryone:
    """Tests for delete_message() with mode='everyone'."""

    def test_delete_for_everyone_success(self, db_session: Session, test_conversation, test_user):
        """
        Test that 'delete for everyone' soft-deletes the message.

        Verifies:
        - is_deleted is set to True
        - deleted_at is set
        - deleted_by is set
        - delete_type is 'everyone'
        - Row is preserved
        - Attachment/metadata preserved
        """
        msg = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="sensitive_content",
            content_hash="hash_everyone",
            message_type="text",
        )

        deleted = delete_message(
            db=db_session,
            message_id=msg.id,
            user_id=test_user.id,
            mode="everyone",
        )

        assert deleted is not None
        assert deleted.id == msg.id
        assert deleted.is_deleted is True
        assert deleted.deleted_at is not None
        assert deleted.deleted_by == test_user.id
        assert deleted.delete_type == "everyone"
        # Row preserved
        assert db_session.query(Message).filter(Message.id == msg.id).first() is not None
        # Message preserved in conversation listing as a placeholder
        # (Issue 5B: delete-for-everyone should show "This message was deleted.")
        messages = get_conversation_messages(
            db=db_session,
            conversation_id=test_conversation.id,
            user_id=test_user.id,
        )
        assert any(m.id == msg.id for m in messages)
        # Verify it is marked as deleted in the listing
        returned = [m for m in messages if m.id == msg.id][0]
        assert returned.is_deleted is True
        assert returned.delete_type == "everyone"

    def test_delete_for_everyone_preserves_message_id(self, db_session: Session, test_conversation, test_user):
        """
        Test that deleting for everyone preserves the message ID.
        """
        msg = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="id_preservation",
            content_hash="hash_id",
            message_type="text",
        )
        original_id = msg.id

        delete_message(
            db=db_session,
            message_id=msg.id,
            user_id=test_user.id,
            mode="everyone",
        )

        assert msg.id == original_id

    def test_delete_for_everyone_updates_conversation_timestamp(
        self, db_session: Session, test_conversation, test_user
    ):
        """
        Test that deleting for everyone updates the conversation's updated_at.
        """
        msg = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="timestamp_test",
            content_hash="hash_ts",
            message_type="text",
        )

        original_updated = test_conversation.updated_at

        delete_message(
            db=db_session,
            message_id=msg.id,
            user_id=test_user.id,
            mode="everyone",
        )

        db_session.refresh(test_conversation)
        assert test_conversation.updated_at >= original_updated


class TestDeleteMessageValidation:
    """Tests for delete_message() validation and security checks."""

    def test_already_deleted_message_rejected(
        self, db_session: Session, test_conversation, test_user
    ):
        """
        Test that deleting an already-deleted message is rejected.
        """
        msg = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="already_deleted",
            content_hash="hash_del",
            message_type="text",
        )

        delete_message(
            db=db_session,
            message_id=msg.id,
            user_id=test_user.id,
            mode="everyone",
        )

        with pytest.raises(ValueError) as exc_info:
            delete_message(
                db=db_session,
                message_id=msg.id,
                user_id=test_user.id,
                mode="me",
            )

        assert "already deleted" in str(exc_info.value).lower()

    def test_system_message_cannot_be_deleted(
        self, db_session: Session, test_conversation, test_user
    ):
        """
        Test that system messages cannot be deleted.
        """
        msg = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="system_content",
            content_hash="hash_sys",
            message_type="system",
        )

        with pytest.raises(ValueError) as exc_info:
            delete_message(
                db=db_session,
                message_id=msg.id,
                user_id=test_user.id,
                mode="everyone",
            )

        assert "system" in str(exc_info.value).lower()

    def test_nonexistent_message_rejected(self, db_session: Session, test_conversation, test_user):
        """
        Test that deleting a non-existent message is rejected.
        """
        fake_id = uuid.uuid4()

        with pytest.raises(ValueError) as exc_info:
            delete_message(
                db=db_session,
                message_id=fake_id,
                user_id=test_user.id,
                mode="me",
            )

        assert "not found" in str(exc_info.value).lower()

    def test_delete_for_everyone_non_owner_rejected(
        self, db_session: Session, test_conversation, test_user, test_user2
    ):
        """
        Test that a non-owner cannot delete for everyone.
        """
        msg = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="owner_content",
            content_hash="hash_own",
            message_type="text",
        )

        with pytest.raises(ValueError) as exc_info:
            delete_message(
                db=db_session,
                message_id=msg.id,
                user_id=test_user2.id,
                mode="everyone",
            )

        assert "own messages" in str(exc_info.value).lower()

    def test_cross_conversation_delete_rejected(
        self, db_session: Session, test_conversation, test_user, test_user2
    ):
        """
        Test that a user cannot delete a message in a conversation they're not part of.
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

        p2 = ConversationParticipant(
            conversation_id=conv2.id,
            user_id=test_user2.id,
            role="admin",
        )
        db_session.add(p2)
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

        # test_user is not a participant in conv2, tries to delete
        with pytest.raises(ValueError) as exc_info:
            delete_message(
                db=db_session,
                message_id=msg_in_conv2.id,
                user_id=test_user.id,
                mode="everyone",
            )

        assert "participant" in str(exc_info.value).lower() or "own" in str(exc_info.value).lower()

    def test_invalid_delete_mode_rejected(self, db_session: Session, test_conversation, test_user):
        """
        Test that an invalid delete mode is rejected.
        """
        msg = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="invalid_mode",
            content_hash="hash_im",
            message_type="text",
        )

        with pytest.raises(ValueError) as exc_info:
            delete_message(
                db=db_session,
                message_id=msg.id,
                user_id=test_user.id,
                mode="invalid",
            )

        assert "invalid" in str(exc_info.value).lower() or "mode" in str(exc_info.value).lower()

    def test_non_participant_cannot_delete(
        self, db_session: Session, test_conversation, test_user
    ):
        """
        Test that a non-participant cannot delete messages.
        """
        msg = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="non_participant_test",
            content_hash="hash_np",
            message_type="text",
        )

        non_participant_id = uuid.uuid4()

        with pytest.raises(ValueError) as exc_info:
            delete_message(
                db=db_session,
                message_id=msg.id,
                user_id=non_participant_id,
                mode="me",
            )

        assert "participant" in str(exc_info.value).lower()
