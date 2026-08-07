"""Security and toggle behavior tests for message reactions."""

import uuid

from core.security import create_access_token
from models.message import Message
from models.user import User
from core.security import hash_password


def _headers(user):
    return {
        "Authorization": f"Bearer {create_access_token(subject=str(user.id))}",
        "Content-Type": "application/json",
    }


class TestMessageReactions:
    def test_add_and_toggle_reaction(self, client, test_message, test_user):
        url = f"/api/v1/messages/{test_message.id}/reactions"
        headers = _headers(test_user)

        added = client.post(url, json={"emoji": "👍"}, headers=headers)
        assert added.status_code == 200
        assert added.json()["reactions"][0]["count"] == 1
        assert added.json()["reactions"][0]["reacted_by_me"] is True

        removed = client.post(url, json={"emoji": "👍"}, headers=headers)
        assert removed.status_code == 200
        assert removed.json()["reactions"] == []

    def test_multiple_emojis_and_users(self, client, test_message, test_user, test_user2):
        url = f"/api/v1/messages/{test_message.id}/reactions"
        assert client.post(url, json={"emoji": "👍"}, headers=_headers(test_user)).status_code == 200
        result = client.post(url, json={"emoji": "❤️"}, headers=_headers(test_user2))
        assert result.status_code == 200
        assert {item["emoji"] for item in result.json()["reactions"]} == {"👍", "❤️"}

    def test_rejects_invalid_and_system_reactions(
        self, client, db_session, test_message, test_user, test_conversation
    ):
        url = f"/api/v1/messages/{test_message.id}/reactions"
        assert client.post(url, json={"emoji": "not emoji"}, headers=_headers(test_user)).status_code == 400
        system = Message(
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="system",
            content_hash="hash",
            message_type="system",
        )
        db_session.add(system)
        db_session.commit()
        assert client.post(
            f"/api/v1/messages/{system.id}/reactions",
            json={"emoji": "👍"},
            headers=_headers(test_user),
        ).status_code == 400

    def test_rejects_idor_and_deleted_messages(
        self, client, test_message, test_user2, db_session
    ):
        url = f"/api/v1/messages/{test_message.id}/reactions"
        outsider = User(
            username=f"outsider_{uuid.uuid4().hex[:8]}",
            email=f"outsider_{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password("testpassword123"),
            is_active=True,
            is_verified=True,
        )
        db_session.add(outsider)
        db_session.commit()
        assert client.post(url, json={"emoji": "👍"}, headers=_headers(outsider)).status_code == 403
        db_session.refresh(test_message)
        test_message.is_deleted = True
        db_session.commit()
        assert client.post(url, json={"emoji": "😂"}, headers=_headers(test_user2)).status_code == 400
        assert client.post(
            f"/api/v1/messages/{uuid.uuid4()}/reactions",
            json={"emoji": "👍"},
            headers=_headers(test_user2),
        ).status_code == 404
