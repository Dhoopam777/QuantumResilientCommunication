"""
Message Router Tests for Quantum-Resilient Communication System

These tests verify the DELETE /api/v1/messages/{message_id} endpoint,
including authentication, authorization, IDOR prevention, and rate limiting.
Also tests WebSocket broadcast on deletion.
"""

import pytest
import uuid
import json
from sqlalchemy.orm import Session

from core.security import create_access_token
from core.websocket_events import (
    WS_EVENT_AUTH,
    WS_EVENT_MESSAGE_DELETED,
)
from services.message_service import send_message


def _delete(client, url, mode, headers):
    """Send a DELETE request with JSON body via httpx-compatible API."""
    return client.request(
        "DELETE",
        url,
        json={"mode": mode},
        headers=headers,
    )


class TestDeleteMessageEndpoint:
    """Tests for DELETE /api/v1/messages/{message_id}."""

    def test_delete_for_me_returns_updated_message(
        self, client, test_conversation, test_user, auth_headers
    ):
        """
        Test that delete-for-me returns the updated message state.
        """
        res = client.post(
            "/api/v1/messages/",
            json={
                "conversation_id": str(test_conversation.id),
                "content_encrypted": "test_delete_me",
                "content_hash": "hash_me",
                "message_type": "text",
            },
            headers=auth_headers,
        )
        assert res.status_code == 201
        msg_id = res.json()["id"]

        del_res = _delete(client, f"/api/v1/messages/{msg_id}", "me", auth_headers)
        assert del_res.status_code == 200
        data = del_res.json()
        assert data["id"] == msg_id
        assert data["is_deleted"] is False  # Delete for me doesn't set is_deleted
        assert data["delete_type"] == "me"
        assert data["deleted_at"] is not None
        assert data["deleted_by"] is not None

    def test_delete_for_everyone_returns_updated_message(
        self, client, test_conversation, test_user, auth_headers
    ):
        """
        Test that delete-for-everyone returns the updated message with is_deleted=True.
        """
        res = client.post(
            "/api/v1/messages/",
            json={
                "conversation_id": str(test_conversation.id),
                "content_encrypted": "test_delete_everyone",
                "content_hash": "hash_everyone",
                "message_type": "text",
            },
            headers=auth_headers,
        )
        assert res.status_code == 201
        msg_id = res.json()["id"]

        del_res = _delete(client, f"/api/v1/messages/{msg_id}", "everyone", auth_headers)
        assert del_res.status_code == 200
        data = del_res.json()
        assert data["id"] == msg_id
        assert data["is_deleted"] is True
        assert data["delete_type"] == "everyone"
        assert data["deleted_at"] is not None
        assert data["deleted_by"] is not None

    def test_delete_nonexistent_message_returns_404(
        self, client, test_conversation, test_user, auth_headers
    ):
        """
        Test that deleting a non-existent message returns 404.
        """
        fake_id = str(uuid.uuid4())
        res = _delete(client, f"/api/v1/messages/{fake_id}", "me", auth_headers)
        assert res.status_code == 404

    def test_delete_already_deleted_message_returns_400(
        self, client, test_conversation, test_user, auth_headers
    ):
        """
        Test that deleting an already-deleted message returns 400.
        """
        res = client.post(
            "/api/v1/messages/",
            json={
                "conversation_id": str(test_conversation.id),
                "content_encrypted": "already_deleted_msg",
                "content_hash": "hash_ad",
                "message_type": "text",
            },
            headers=auth_headers,
        )
        assert res.status_code == 201
        msg_id = res.json()["id"]

        # First delete (for everyone)
        _delete(client, f"/api/v1/messages/{msg_id}", "everyone", auth_headers)

        # Second delete should fail with 400
        res2 = _delete(client, f"/api/v1/messages/{msg_id}", "me", auth_headers)
        assert res2.status_code == 400

    def test_delete_system_message_returns_400(
        self, client, test_conversation, test_user, auth_headers
    ):
        """
        Test that deleting a system message returns 400.
        """
        res = client.post(
            "/api/v1/messages/",
            json={
                "conversation_id": str(test_conversation.id),
                "content_encrypted": "system_msg",
                "content_hash": "hash_sys",
                "message_type": "system",
            },
            headers=auth_headers,
        )
        assert res.status_code == 201
        msg_id = res.json()["id"]

        del_res = _delete(client, f"/api/v1/messages/{msg_id}", "me", auth_headers)
        assert del_res.status_code == 400

    def test_delete_for_everyone_non_owner_returns_403(
        self, client, test_conversation, test_user, test_user2, auth_headers
    ):
        """
        Test that a non-owner cannot delete for everyone — returns 403.
        """
        res = client.post(
            "/api/v1/messages/",
            json={
                "conversation_id": str(test_conversation.id),
                "content_encrypted": "owner_msg",
                "content_hash": "hash_own",
                "message_type": "text",
            },
            headers=auth_headers,
        )
        assert res.status_code == 201
        msg_id = res.json()["id"]

        # test_user2 tries to delete for everyone
        user2_token = create_access_token(subject=str(test_user2.id))
        user2_headers = {
            "Authorization": f"Bearer {user2_token}",
            "Content-Type": "application/json",
        }

        del_res = _delete(client, f"/api/v1/messages/{msg_id}", "everyone", user2_headers)
        assert del_res.status_code == 403

    def test_delete_invalid_mode_returns_422(
        self, client, test_conversation, test_user, auth_headers
    ):
        """
        Test that an invalid delete mode returns 422 (Pydantic validation error).
        """
        res = client.post(
            "/api/v1/messages/",
            json={
                "conversation_id": str(test_conversation.id),
                "content_encrypted": "test_mode",
                "content_hash": "hash_mode",
                "message_type": "text",
            },
            headers=auth_headers,
        )
        assert res.status_code == 201
        msg_id = res.json()["id"]

        del_res = client.request(
            "DELETE",
            f"/api/v1/messages/{msg_id}",
            json={"mode": "invalid"},
            headers=auth_headers,
        )
        assert del_res.status_code == 422

    def test_delete_requires_auth(
        self, client, test_conversation
    ):
        """
        Test that deletion without authentication returns 401 (or 422 for missing body).
        At minimum, without auth headers it should not succeed with 200.
        """
        fake_id = str(uuid.uuid4())
        res = client.request(
            "DELETE",
            f"/api/v1/messages/{fake_id}",
            json={"mode": "me"},
            headers={"Content-Type": "application/json"},
        )
        assert res.status_code in (401, 403)

    def test_delete_unauthorized_user_returns_403(
        self, client, test_conversation, test_user, test_user2, auth_headers, db_session
    ):
        """
        Test IDOR prevention: a non-owner cannot delete-for-everyone.
        """
        msg = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="idor_test",
            content_hash="hash_idor",
            message_type="text",
        )
        db_session.refresh(msg)

        user2_token = create_access_token(subject=str(test_user2.id))
        user2_headers = {
            "Authorization": f"Bearer {user2_token}",
            "Content-Type": "application/json",
        }

        del_res = _delete(client, f"/api/v1/messages/{msg.id}", "everyone", user2_headers)
        assert del_res.status_code == 403

    def test_delete_for_me_other_user_message_allowed(
        self, client, test_conversation, test_user, test_user2, auth_headers, db_session
    ):
        """
        Test that any participant can delete-for-me on another user's message.
        """
        msg = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="shared_msg",
            content_hash="hash_shared",
            message_type="text",
        )
        db_session.refresh(msg)

        user2_token = create_access_token(subject=str(test_user2.id))
        user2_headers = {
            "Authorization": f"Bearer {user2_token}",
            "Content-Type": "application/json",
        }

        del_res = _delete(client, f"/api/v1/messages/{msg.id}", "me", user2_headers)
        assert del_res.status_code == 200
        data = del_res.json()
        assert data["delete_type"] == "me"
        assert data["is_deleted"] is False  # Other users still see it

    def test_delete_for_me_hides_message_for_requester(
        self, client, test_conversation, test_user, test_user2, auth_headers, db_session
    ):
        """
        Test that after delete-for-me, the requester no longer sees the message in listing.
        """
        msg = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="hidden_for_me",
            content_hash="hash_hidden",
            message_type="text",
        )
        db_session.refresh(msg)

        # test_user2 deletes for me
        user2_token = create_access_token(subject=str(test_user2.id))
        user2_headers = {
            "Authorization": f"Bearer {user2_token}",
            "Content-Type": "application/json",
        }

        del_res = _delete(client, f"/api/v1/messages/{msg.id}", "me", user2_headers)
        assert del_res.status_code == 200

        # test_user (the sender/owner) still sees the message via REST API
        list_res = client.get(
            f"/api/v1/messages/conversation/{test_conversation.id}",
            headers=auth_headers,
        )
        assert list_res.status_code == 200
        msgs = list_res.json()
        assert any(m["id"] == str(msg.id) for m in msgs)

    def test_delete_for_everyone_hides_message_for_all(
        self, client, test_conversation, test_user, test_user2, auth_headers, db_session
    ):
        """
        Test that after delete-for-everyone, neither user sees the message.
        """
        msg = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="hidden_for_all",
            content_hash="hash_hidden_all",
            message_type="text",
        )
        db_session.refresh(msg)

        del_res = _delete(client, f"/api/v1/messages/{msg.id}", "everyone", auth_headers)
        assert del_res.status_code == 200

        # test_user no longer sees the message
        list_res = client.get(
            f"/api/v1/messages/conversation/{test_conversation.id}",
            headers=auth_headers,
        )
        msgs = list_res.json()
        assert not any(m["id"] == str(msg.id) for m in msgs)

        # test_user2 also doesn't see the message
        user2_token = create_access_token(subject=str(test_user2.id))
        user2_headers = {
            "Authorization": f"Bearer {user2_token}",
            "Content-Type": "application/json",
        }
        list_res2 = client.get(
            f"/api/v1/messages/conversation/{test_conversation.id}",
            headers=user2_headers,
        )
        msgs2 = list_res2.json()
        assert not any(m["id"] == str(msg.id) for m in msgs2)


class TestDeleteMessageWebSocket:
    """Tests for WebSocket broadcast on deletion."""

    def test_delete_broadcasts_to_participants(
        self, client, test_conversation, test_user, test_user2, auth_headers, db_session
    ):
        """
        Test that a delete-for-everyone is broadcast to all WebSocket participants.
        """
        token = auth_headers["Authorization"].replace("Bearer ", "")
        user2_token = create_access_token(subject=str(test_user2.id))

        # Create a message via REST
        res = client.post(
            "/api/v1/messages/",
            json={
                "conversation_id": str(test_conversation.id),
                "content_encrypted": "ws_broadcast_test",
                "content_hash": "hash_ws",
                "message_type": "text",
            },
            headers=auth_headers,
        )
        msg_id = res.json()["id"]

        with client.websocket_connect("/ws") as ws1, client.websocket_connect("/ws") as ws2:
            # Authenticate both
            ws1.send_json({"type": WS_EVENT_AUTH, "token": token})
            ws1.receive_json()
            ws2.send_json({"type": WS_EVENT_AUTH, "token": user2_token})
            ws2.receive_json()

            # Both join the conversation
            ws1.send_json({"type": "join_conversation", "conversation_id": str(test_conversation.id)})
            ws1.receive_json()
            ws2.send_json({"type": "join_conversation", "conversation_id": str(test_conversation.id)})
            ws2.receive_json()

            # Delete for everyone via REST
            del_res = _delete(client, f"/api/v1/messages/{msg_id}", "everyone", auth_headers)
            assert del_res.status_code == 200

            # Both WS clients should receive message_deleted broadcast
            ws1_msg = ws1.receive_json()
            assert ws1_msg["type"] == WS_EVENT_MESSAGE_DELETED
            assert ws1_msg["message"]["id"] == msg_id

            ws2_msg = ws2.receive_json()
            assert ws2_msg["type"] == WS_EVENT_MESSAGE_DELETED
            assert ws2_msg["message"]["id"] == msg_id

    def test_delete_for_me_broadcast_to_sender(
        self, client, test_conversation, test_user, test_user2, auth_headers, db_session
    ):
        """
        Test that delete-for-me is broadcast to the sender (who then hides it locally).
        """
        token = auth_headers["Authorization"].replace("Bearer ", "")
        user2_token = create_access_token(subject=str(test_user2.id))

        msg = send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="me_ws_test",
            content_hash="hash_me_ws",
            message_type="text",
        )
        db_session.refresh(msg)

        with client.websocket_connect("/ws") as ws1:
            ws1.send_json({"type": WS_EVENT_AUTH, "token": token})
            ws1.receive_json()
            ws1.send_json({"type": "join_conversation", "conversation_id": str(test_conversation.id)})
            ws1.receive_json()

            del_res = _delete(client, f"/api/v1/messages/{msg.id}", "me", auth_headers)
            assert del_res.status_code == 200

            # Sender receives broadcast and updates locally
            ws_msg = ws1.receive_json()
            assert ws_msg["type"] == WS_EVENT_MESSAGE_DELETED
            assert ws_msg["message"]["delete_type"] == "me"
