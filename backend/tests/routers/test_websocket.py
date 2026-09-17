"""
WebSocket Router Tests for Quantum-Resilient Communication System

These tests verify the WebSocket endpoint at /ws, including:
  - Connection lifecycle (accept, disconnect, cleanup)
  - JWT authentication (valid, invalid, expired tokens)
  - Per-conversation authorization (IDOR prevention)
  - Broadcast integration (REST POST → WebSocket delivery)
  - Connection cleanup on disconnect
"""

import json
import uuid

import anyio
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from core.security import create_access_token, decode_token
from core.websocket_events import (
    WS_EVENT_AUTH,
    WS_EVENT_AUTH_SUCCESS,
    WS_EVENT_AUTH_ERROR,
    WS_EVENT_JOIN_CONVERSATION,
    WS_EVENT_JOINED_CONVERSATION,
    WS_EVENT_LEAVE_CONVERSATION,
    WS_EVENT_LEFT_CONVERSATION,
    WS_EVENT_PING,
    WS_EVENT_PONG,
    WS_EVENT_NEW_MESSAGE,
    WS_EVENT_ERROR,
    WS_CLOSE_AUTH_FAILED,
    WS_CLOSE_FORBIDDEN,
)
from managers.connection_manager import connection_manager

from tests.pqc_helpers import install_signing_api_calls


@pytest.fixture(autouse=True)
def _client_signs_messages(client, db_session, monkeypatch):
    # Model a real client: message-creation requests carry device signatures.
    install_signing_api_calls(client, db_session, monkeypatch)



class TestWebSocketAuth:
    """Tests for WebSocket authentication."""

    def test_auth_with_valid_token(self, client: TestClient, test_user, auth_headers):
        """
        Test that a valid JWT access token authenticates the connection.
        Expects auth_success with user_id and username.
        """
        token = auth_headers["Authorization"].replace("Bearer ", "")

        with client.websocket_connect("/ws") as ws:
            # Send auth message
            ws.send_json({"type": WS_EVENT_AUTH, "token": token})

            # Receive auth_success
            response = ws.receive_json()
            assert response["type"] == WS_EVENT_AUTH_SUCCESS
            assert response["user_id"] == str(test_user.id)
            assert response["username"] == test_user.username

    def test_auth_with_invalid_token(self, client: TestClient):
        """
        Test that an invalid JWT is rejected.
        Expects auth_error and connection close with code 4401.
        """
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": WS_EVENT_AUTH, "token": "invalid_token_here"})

            # Receive auth_error
            response = ws.receive_json()
            assert response["type"] == WS_EVENT_AUTH_ERROR
            assert "error" in response

            # Connection should be closed
            with pytest.raises(Exception):
                ws.receive_json()

    def test_auth_with_expired_token(self, client: TestClient, test_user):
        """
        Test that an expired JWT is rejected.
        Expects auth_error and connection close with code 4401.
        """
        # Create a token that's already expired
        from datetime import datetime, timedelta, timezone
        from jose import jwt
        from core.config import settings

        expired_payload = {
            "sub": str(test_user.id),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "type": "access",
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        }
        expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm="HS256")

        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": WS_EVENT_AUTH, "token": expired_token})

            response = ws.receive_json()
            assert response["type"] == WS_EVENT_AUTH_ERROR

            with pytest.raises(Exception):
                ws.receive_json()

    def test_auth_with_refresh_token_rejected(self, client: TestClient, test_user):
        """
        Test that a refresh token is rejected (only access tokens allowed).
        """
        from core.security import create_refresh_token

        refresh_token = create_refresh_token(subject=str(test_user.id))

        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": WS_EVENT_AUTH, "token": refresh_token})

            response = ws.receive_json()
            assert response["type"] == WS_EVENT_AUTH_ERROR

            with pytest.raises(Exception):
                ws.receive_json()

    def test_auth_without_token(self, client: TestClient):
        """
        Test that missing token is rejected.
        """
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": WS_EVENT_AUTH, "token": ""})

            response = ws.receive_json()
            assert response["type"] == WS_EVENT_AUTH_ERROR

            with pytest.raises(Exception):
                ws.receive_json()

    def test_unauthenticated_action_rejected(self, client: TestClient):
        """
        Test that any action before auth is rejected.
        """
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": WS_EVENT_JOIN_CONVERSATION, "conversation_id": str(uuid.uuid4())})

            response = ws.receive_json()
            assert response["type"] == WS_EVENT_ERROR
            assert "auth" in response.get("error", "").lower()

            with pytest.raises(Exception):
                ws.receive_json()


class TestWebSocketAuthorization:
    """Tests for per-conversation authorization (IDOR prevention)."""

    def test_join_conversation_as_participant(
        self, client: TestClient, test_conversation, auth_headers
    ):
        """
        Test that a participant can join a conversation.
        Expects joined_conversation.
        """
        token = auth_headers["Authorization"].replace("Bearer ", "")

        with client.websocket_connect("/ws") as ws:
            # Authenticate
            ws.send_json({"type": WS_EVENT_AUTH, "token": token})
            auth_resp = ws.receive_json()
            assert auth_resp["type"] == WS_EVENT_AUTH_SUCCESS

            # Join conversation
            ws.send_json({
                "type": WS_EVENT_JOIN_CONVERSATION,
                "conversation_id": str(test_conversation.id),
            })
            join_resp = ws.receive_json()
            assert join_resp["type"] == WS_EVENT_JOINED_CONVERSATION
            assert join_resp["conversation_id"] == str(test_conversation.id)

    def test_join_conversation_as_non_participant(
        self, client: TestClient, db_session, test_user, test_user2, auth_headers
    ):
        """
        Test that a non-participant is rejected (IDOR prevention).
        Expects error and connection close with code 4403.
        """
        token = auth_headers["Authorization"].replace("Bearer ", "")

        # Create a conversation the test user is NOT a participant of
        from models.conversation import Conversation
        from models.conversation_participant import ConversationParticipant

        convo = Conversation(is_group=False, created_by=test_user2.id)
        db_session.add(convo)
        db_session.flush()
        participant = ConversationParticipant(
            conversation_id=convo.id, user_id=test_user2.id, role="admin"
        )
        db_session.add(participant)
        db_session.commit()

        with client.websocket_connect("/ws") as ws:
            # Authenticate
            ws.send_json({"type": WS_EVENT_AUTH, "token": token})
            auth_resp = ws.receive_json()
            assert auth_resp["type"] == WS_EVENT_AUTH_SUCCESS

            # Try to join conversation we're not in
            ws.send_json({
                "type": WS_EVENT_JOIN_CONVERSATION,
                "conversation_id": str(convo.id),
            })
            error_resp = ws.receive_json()
            assert error_resp["type"] == WS_EVENT_ERROR
            assert "participant" in error_resp.get("error", "").lower()

            # Connection should be closed
            with pytest.raises(Exception):
                ws.receive_json()

    def test_join_nonexistent_conversation(
        self, client: TestClient, auth_headers
    ):
        """
        Test that joining a non-existent conversation is rejected.
        """
        token = auth_headers["Authorization"].replace("Bearer ", "")
        fake_id = uuid.uuid4()

        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": WS_EVENT_AUTH, "token": token})
            auth_resp = ws.receive_json()
            assert auth_resp["type"] == WS_EVENT_AUTH_SUCCESS

            ws.send_json({
                "type": WS_EVENT_JOIN_CONVERSATION,
                "conversation_id": str(fake_id),
            })
            error_resp = ws.receive_json()
            assert error_resp["type"] == WS_EVENT_ERROR

            with pytest.raises(Exception):
                ws.receive_json()

    def test_leave_conversation(
        self, client: TestClient, test_conversation, auth_headers
    ):
        """
        Test that a participant can leave a conversation.
        """
        token = auth_headers["Authorization"].replace("Bearer ", "")

        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": WS_EVENT_AUTH, "token": token})
            ws.receive_json()  # auth_success

            # Join
            ws.send_json({
                "type": WS_EVENT_JOIN_CONVERSATION,
                "conversation_id": str(test_conversation.id),
            })
            ws.receive_json()  # joined_conversation

            # Leave
            ws.send_json({
                "type": WS_EVENT_LEAVE_CONVERSATION,
                "conversation_id": str(test_conversation.id),
            })
            leave_resp = ws.receive_json()
            assert leave_resp["type"] == WS_EVENT_LEFT_CONVERSATION
            assert leave_resp["conversation_id"] == str(test_conversation.id)


class TestWebSocketPing:
    """Tests for WebSocket heartbeat."""

    def test_ping_pong(self, client: TestClient, auth_headers):
        """
        Test that ping receives a pong response.
        """
        token = auth_headers["Authorization"].replace("Bearer ", "")

        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": WS_EVENT_AUTH, "token": token})
            ws.receive_json()  # auth_success

            ws.send_json({"type": WS_EVENT_PING})
            pong_resp = ws.receive_json()
            assert pong_resp["type"] == WS_EVENT_PONG


class TestWebSocketBroadcast:
    """Tests for message broadcasting via WebSocket."""

    def test_broadcast_to_participants(
        self, client: TestClient, test_conversation, test_user, test_user2, auth_headers
    ):
        """
        Test that a message sent via REST POST is broadcast to all
        connected WebSocket participants of that conversation.
        """
        token = auth_headers["Authorization"].replace("Bearer ", "")

        # Create a second auth header for user2
        from core.security import create_access_token
        user2_token = create_access_token(subject=str(test_user2.id))

        # Connect two WebSocket clients (user1 and user2)
        with client.websocket_connect("/ws") as ws1, client.websocket_connect("/ws") as ws2:
            # Authenticate both
            ws1.send_json({"type": WS_EVENT_AUTH, "token": token})
            ws1.receive_json()  # auth_success

            ws2.send_json({"type": WS_EVENT_AUTH, "token": user2_token})
            ws2.receive_json()  # auth_success

            # Both join the conversation
            ws1.send_json({
                "type": WS_EVENT_JOIN_CONVERSATION,
                "conversation_id": str(test_conversation.id),
            })
            ws1.receive_json()  # joined_conversation

            ws2.send_json({
                "type": WS_EVENT_JOIN_CONVERSATION,
                "conversation_id": str(test_conversation.id),
            })
            ws2.receive_json()  # joined_conversation

            # Send a message via REST POST
            response = client.post(
                "/api/v1/messages/",
                json={
                    "conversation_id": str(test_conversation.id),
                    "content_encrypted": "test_broadcast_message",
                    "content_hash": "test_hash_123",
                    "message_type": "text",
                },
                headers=auth_headers,
            )
            assert response.status_code == 201

            # Both WebSocket clients should receive the broadcast
            ws1_msg = ws1.receive_json()
            assert ws1_msg["type"] == WS_EVENT_NEW_MESSAGE
            assert ws1_msg["message"]["content_encrypted"] == "test_broadcast_message"

            ws2_msg = ws2.receive_json()
            assert ws2_msg["type"] == WS_EVENT_NEW_MESSAGE
            assert ws2_msg["message"]["content_encrypted"] == "test_broadcast_message"

    def test_no_broadcast_to_non_subscriber(
        self, client: TestClient, test_conversation, test_user, test_user2, auth_headers
    ):
        """
        Test that a user not subscribed to a conversation does NOT
        receive the broadcast (IDOR prevention).
        """
        token = auth_headers["Authorization"].replace("Bearer ", "")
        from core.security import create_access_token
        user2_token = create_access_token(subject=str(test_user2.id))

        with client.websocket_connect("/ws") as ws1, client.websocket_connect("/ws") as ws2:
            # Authenticate both
            ws1.send_json({"type": WS_EVENT_AUTH, "token": token})
            ws1.receive_json()

            ws2.send_json({"type": WS_EVENT_AUTH, "token": user2_token})
            ws2.receive_json()

            # Only ws1 joins the conversation
            ws1.send_json({
                "type": WS_EVENT_JOIN_CONVERSATION,
                "conversation_id": str(test_conversation.id),
            })
            ws1.receive_json()

            # Send a message via REST POST
            response = client.post(
                "/api/v1/messages/",
                json={
                    "conversation_id": str(test_conversation.id),
                    "content_encrypted": "private_message",
                    "content_hash": "hash_456",
                    "message_type": "text",
                },
                headers=auth_headers,
            )
            assert response.status_code == 201

            # ws1 receives the broadcast
            ws1_msg = ws1.receive_json()
            assert ws1_msg["type"] == WS_EVENT_NEW_MESSAGE

            # ws2 should NOT receive the broadcast (not subscribed)
            with pytest.raises(Exception):
                ws2.receive_json(timeout=1)


class TestWebSocketConnectionLifecycle:
    """Tests for connection lifecycle management."""

    def test_disconnect_cleans_up(self, client: TestClient, test_conversation, auth_headers):
        """
        Test that disconnecting a WebSocket cleans up all subscriptions.
        """
        token = auth_headers["Authorization"].replace("Bearer ", "")

        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": WS_EVENT_AUTH, "token": token})
            ws.receive_json()

            ws.send_json({
                "type": WS_EVENT_JOIN_CONVERSATION,
                "conversation_id": str(test_conversation.id),
            })
            ws.receive_json()

            # Verify subscription exists
            assert connection_manager.get_subscription_count(test_conversation.id) == 1

            ws.close()
            ws.portal.call(anyio.sleep, 0)

        # After the disconnect event is processed, subscriptions are cleaned up.
        assert connection_manager.get_subscription_count(test_conversation.id) == 0

    def test_connection_count_tracking(self, client: TestClient, auth_headers):
        """
        Test that connection count is tracked correctly.
        """
        token = auth_headers["Authorization"].replace("Bearer ", "")
        initial_count = connection_manager.get_connection_count()

        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": WS_EVENT_AUTH, "token": token})
            ws.receive_json()
            assert connection_manager.get_connection_count() == initial_count + 1

            ws.close()
            ws.portal.call(anyio.sleep, 0)

        assert connection_manager.get_connection_count() == initial_count
