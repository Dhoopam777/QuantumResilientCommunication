"""Email verification lifecycle and activation restriction tests."""

import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from core.rate_limiter import RateLimiter
from core.security import create_access_token, hash_password
from models.user import User


class CapturingSender:
    def __init__(self):
        self.links = []
        self.recipients = []

    def send_verification(self, recipient, link):
        self.recipients.append(recipient)
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


def test_unverified_user_cannot_log_in(client, db_session, test_user):
    test_user.is_email_verified = False
    test_user.is_verified = False
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": test_user.username, "password": "testpassword123"},
    )

    assert response.status_code == 403
    assert "verification" in response.json()["detail"].lower()


def _create_unverified_user(db_session, email, username=None):
    """Create an active account that has not verified its email yet."""
    user = User(
        username=username or f"unverified_{uuid.uuid4().hex[:8]}",
        email=email,
        password_hash=hash_password("testpassword123"),
        full_name="Unverified User",
        is_active=True,
        is_verified=False,
        is_email_verified=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


GENERIC_RESEND_MESSAGE = (
    "If that email belongs to an unverified account, "
    "a fresh verification link has been sent."
)


def test_public_resend_sends_fresh_link_to_unverified_account(client, db_session, monkeypatch):
    sender = CapturingSender()
    monkeypatch.setattr("services.email_verification_service.get_email_sender", lambda: sender)
    email = f"resend_{uuid.uuid4().hex[:8]}@example.com"
    user = _create_unverified_user(db_session, email)

    response = client.post("/api/v1/auth/resend-verification", json={"email": email})

    assert response.status_code == 200
    assert response.json()["detail"] == GENERIC_RESEND_MESSAGE
    assert sender.recipients == [email]
    assert len(sender.links) == 1
    assert "token=" in sender.links[0]
    token = parse_qs(urlparse(sender.links[0]).query)["token"][0]

    db_session.refresh(user)
    assert user.is_email_verified is False
    assert user.verification_token_hash is not None
    # The plaintext token must never be stored in the database.
    assert token not in user.verification_token_hash
    assert user.verification_token_expires_at is not None


def test_public_resend_returns_generic_response_for_nonexistent_email(client, db_session, monkeypatch):
    sender = CapturingSender()
    monkeypatch.setattr("services.email_verification_service.get_email_sender", lambda: sender)
    email = f"nobody_{uuid.uuid4().hex[:8]}@example.com"

    response = client.post("/api/v1/auth/resend-verification", json={"email": email})

    # Identical response to the success case — no account enumeration.
    assert response.status_code == 200
    assert response.json()["detail"] == GENERIC_RESEND_MESSAGE
    assert sender.links == []


def test_public_resend_does_not_send_to_verified_email(client, db_session, test_user, monkeypatch):
    sender = CapturingSender()
    monkeypatch.setattr("services.email_verification_service.get_email_sender", lambda: sender)

    response = client.post("/api/v1/auth/resend-verification", json={"email": test_user.email})

    assert response.status_code == 200
    assert response.json()["detail"] == GENERIC_RESEND_MESSAGE
    assert sender.links == []
    db_session.refresh(test_user)
    assert test_user.verification_token_hash is None


def test_public_resend_is_rate_limited_per_email(client, db_session, monkeypatch):
    sender = CapturingSender()
    monkeypatch.setattr("services.email_verification_service.get_email_sender", lambda: sender)
    # Deterministic limit independent of environment settings.
    monkeypatch.setattr(
        "routers.auth.rate_limiter",
        RateLimiter(max_verification_resends_per_hour=3),
    )
    email = f"ratelimit_{uuid.uuid4().hex[:8]}@example.com"
    _create_unverified_user(db_session, email)

    for _ in range(3):
        response = client.post("/api/v1/auth/resend-verification", json={"email": email})
        assert response.status_code == 200

    response = client.post("/api/v1/auth/resend-verification", json={"email": email})
    assert response.status_code == 429
    assert len(sender.links) == 3
