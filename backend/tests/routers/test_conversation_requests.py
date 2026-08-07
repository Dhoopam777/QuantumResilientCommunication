"""Security and lifecycle tests for conversation requests."""

import uuid

from core.security import create_access_token, hash_password
from models.user import User
from services.conversation_service import get_user_conversations


def headers(user):
    return {
        "Authorization": f"Bearer {create_access_token(subject=str(user.id))}",
        "Content-Type": "application/json",
    }


def make_user(db, name):
    user = User(
        username=f"{name}_{uuid.uuid4().hex[:8]}",
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("testpassword123"),
        is_active=True,
        is_verified=True,
        display_name=name.title(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestConversationRequests:
    def test_create_duplicate_and_self_request_rejected(self, client, db_session, test_user):
        receiver = make_user(db_session, "alice")
        result = client.post(
            "/api/v1/conversation-requests",
            json={"username": receiver.username},
            headers=headers(test_user),
        )
        assert result.status_code == 201
        assert client.post(
            "/api/v1/conversation-requests",
            json={"username": receiver.username},
            headers=headers(test_user),
        ).status_code == 400
        assert client.post(
            "/api/v1/conversation-requests",
            json={"username": test_user.username},
            headers=headers(test_user),
        ).status_code == 400

    def test_accept_creates_conversation_only_after_acceptance(self, client, db_session, test_user):
        receiver = make_user(db_session, "alice")
        create = client.post(
            "/api/v1/conversation-requests",
            json={"username": receiver.username},
            headers=headers(test_user),
        )
        request_id = create.json()["id"]
        assert get_user_conversations(db_session, test_user.id) == []

        accepted = client.post(
            f"/api/v1/conversation-requests/{request_id}/accept",
            headers=headers(receiver),
        )
        assert accepted.status_code == 200
        assert accepted.json()["status"] == "ACCEPTED"
        assert len(get_user_conversations(db_session, test_user.id)) == 1
        assert len(get_user_conversations(db_session, receiver.id)) == 1

    def test_idor_decline_cancel_and_private_search(self, client, db_session, test_user):
        receiver = make_user(db_session, "alice")
        outsider = make_user(db_session, "outsider")
        created = client.post(
            "/api/v1/conversation-requests",
            json={"username": receiver.username},
            headers=headers(test_user),
        )
        request_id = created.json()["id"]
        assert client.post(
            f"/api/v1/conversation-requests/{request_id}/decline",
            headers=headers(outsider),
        ).status_code == 403
        assert client.delete(
            f"/api/v1/conversation-requests/{request_id}",
            headers=headers(test_user),
        ).status_code == 200
        search = client.get(
            f"/api/v1/users/search?q={receiver.username[:4]}",
            headers=headers(test_user),
        )
        assert search.status_code == 200
        assert "email" not in search.text
        assert "id" not in search.json()[0]

    def test_receiver_gets_request_websocket_event(self, client, db_session, test_user):
        receiver = make_user(db_session, "alice")
        token = create_access_token(subject=str(receiver.id))
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"type": "auth", "token": token})
            assert websocket.receive_json()["type"] == "auth_success"
            result = client.post(
                "/api/v1/conversation-requests",
                json={"username": receiver.username},
                headers=headers(test_user),
            )
            assert result.status_code == 201
            event = websocket.receive_json()
            assert event["type"] == "conversation_request_received"
            assert event["request"]["sender"]["username"] == test_user.username
