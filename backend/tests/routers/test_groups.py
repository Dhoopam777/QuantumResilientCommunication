"""Security and lifecycle tests for group conversations."""

import uuid

from core.security import create_access_token, hash_password
from models.conversation_participant import ConversationParticipant
from models.user import User


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


def test_create_group_by_username_and_reject_creator_duplicate(client, db_session, test_user):
    alice = make_user(db_session, "alice")
    response = client.post(
        "/api/v1/groups",
        json={"group_name": "Quantum Team", "members": [alice.username]},
        headers=headers(test_user),
    )
    assert response.status_code == 201
    assert response.json()["is_group"] is True
    assert response.json()["group_name"] == "Quantum Team"
    assert len(response.json()["participants"]) == 2

    duplicate_creator = client.post(
        "/api/v1/groups",
        json={"group_name": "Invalid", "members": [test_user.username]},
        headers=headers(test_user),
    )
    assert duplicate_creator.status_code == 400


def test_owner_can_update_add_and_remove_but_cannot_remove_self(
    client, db_session, test_user
):
    alice = make_user(db_session, "alice")
    bob = make_user(db_session, "bob")
    created = client.post(
        "/api/v1/groups",
        json={"group_name": "Team", "members": [alice.username]},
        headers=headers(test_user),
    )
    group_id = created.json()["id"]

    updated = client.put(
        f"/api/v1/groups/{group_id}",
        json={"group_name": "Updated Team", "group_description": "Research"},
        headers=headers(test_user),
    )
    assert updated.status_code == 200
    assert updated.json()["group_description"] == "Research"

    added = client.post(
        f"/api/v1/groups/{group_id}/members",
        json={"username": bob.username},
        headers=headers(test_user),
    )
    assert added.status_code == 200
    assert {p["username"] for p in added.json()["participants"]} == {
        test_user.username, alice.username, bob.username
    }

    removed = client.delete(
        f"/api/v1/groups/{group_id}/members/{bob.username}",
        headers=headers(test_user),
    )
    assert removed.status_code == 200
    assert bob.username not in {p["username"] for p in removed.json()["participants"]}

    self_remove = client.delete(
        f"/api/v1/groups/{group_id}/members/{test_user.username}",
        headers=headers(test_user),
    )
    assert self_remove.status_code == 400


def test_non_owner_and_non_member_are_forbidden(client, db_session, test_user):
    alice = make_user(db_session, "alice")
    outsider = make_user(db_session, "outsider")
    created = client.post(
        "/api/v1/groups",
        json={"group_name": "Team", "members": [alice.username]},
        headers=headers(test_user),
    )
    group_id = created.json()["id"]

    assert client.put(
        f"/api/v1/groups/{group_id}",
        json={"group_name": "Nope"},
        headers=headers(alice),
    ).status_code == 403
    assert client.get(
        f"/api/v1/groups/{group_id}", headers=headers(outsider)
    ).status_code == 403


def test_duplicate_member_is_rejected_and_removed_user_is_unsubscribed(
    client, db_session, test_user
):
    alice = make_user(db_session, "alice")
    created = client.post(
        "/api/v1/groups",
        json={"group_name": "Team", "members": [alice.username]},
        headers=headers(test_user),
    )
    group_id = created.json()["id"]
    duplicate = client.post(
        f"/api/v1/groups/{group_id}/members",
        json={"username": alice.username},
        headers=headers(test_user),
    )
    assert duplicate.status_code == 400
    membership = (
        db_session.query(ConversationParticipant)
        .filter(ConversationParticipant.user_id == alice.id)
        .first()
    )
    assert membership is not None


def test_group_created_and_member_added_events_are_targeted(client, db_session, test_user):
    alice = make_user(db_session, "alice")
    token = create_access_token(subject=str(alice.id))
    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "auth", "token": token})
        assert websocket.receive_json()["type"] == "auth_success"
        created = client.post(
            "/api/v1/groups",
            json={"group_name": "Realtime", "members": [alice.username]},
            headers=headers(test_user),
        )
        assert created.status_code == 201
        event = websocket.receive_json()
        assert event["type"] == "group_created"
        assert event["conversation"]["group_name"] == "Realtime"
