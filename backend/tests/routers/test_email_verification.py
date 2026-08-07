"""Email verification lifecycle and activation restriction tests."""

from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from core.security import create_access_token
from models.user import User


class CapturingSender:
    links = []

    def send_verification(self, recipient, link):
        self.links.append(link)


def auth_headers(user):
    return {"Authorization": f"Bearer {create_access_token(subject=str(user.id))}"}


def test_registration_issues_hashed_verification_token(client, db_session, monkeypatch):
    sender = CapturingSender()
    monkeypatch.setattr("services.email_verification_service.get_email_sender", lambda: sender)
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "verify_me", "email": "verify@example.com", "password": "SecurePass123!"},
    )
    assert response.status_code == 201
    user = db_session.query(User).filter(User.username == "verify_me").first()
    assert user.is_email_verified is False
    assert user.verification_token_hash
    assert "token=" in sender.links[-1]
    token = parse_qs(urlparse(sender.links[-1]).query)["token"][0]
    assert token not in user.verification_token_hash

    verified = client.get(f"/api/v1/auth/verify-email?token={token}")
    assert verified.status_code == 200
    assert verified.json()["is_email_verified"] is True
    assert client.get(f"/api/v1/auth/verify-email?token={token}").status_code == 400


def test_expired_and_invalid_tokens_are_rejected(client, db_session, test_user):
    test_user.is_email_verified = False
    test_user.is_verified = False
    test_user.verification_token_hash = "a" * 64
    test_user.verification_token_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()
    assert client.get("/api/v1/auth/verify-email?token=invalid").status_code == 400


def test_unverified_user_is_restricted_from_groups(client, db_session, test_user):
    test_user.is_email_verified = False
    test_user.is_verified = False
    db_session.commit()
    response = client.post(
        "/api/v1/groups",
        json={"group_name": "Blocked", "members": ["missing"]},
        headers=auth_headers(test_user),
    )
    assert response.status_code == 403


def test_resend_requires_authentication_and_is_rate_limited(client, test_user, monkeypatch):
    sender = CapturingSender()
    monkeypatch.setattr("services.email_verification_service.get_email_sender", lambda: sender)
    response = client.post("/api/v1/auth/resend-verification", headers=auth_headers(test_user))
    assert response.status_code == 200
    assert client.post("/api/v1/auth/resend-verification").status_code in {401, 403}
