"""Secure one-time email verification token lifecycle."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from core.config import settings
from models.user import User
from services.email_service import get_email_sender


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def issue_verification(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    user.verification_token_hash = _hash_token(token)
    user.verification_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    db.commit()
    link = f"{settings.FRONTEND_URL}/test/verify-email?token={token}"
    get_email_sender().send_verification(user.email, link)
    return token


def verify_token(db: Session, token: str) -> User:
    if not token or len(token) > 128:
        raise ValueError("Invalid or expired verification token")
    user = (
        db.query(User)
        .filter(User.verification_token_hash == _hash_token(token))
        .with_for_update()
        .first()
    )
    now = datetime.now(timezone.utc)
    if (
        user is None
        or user.verification_token_expires_at is None
        or user.verification_token_expires_at <= now
        or user.is_email_verified
    ):
        raise ValueError("Invalid or expired verification token")
    user.is_email_verified = True
    user.is_verified = True
    user.email_verified_at = now
    user.verification_token_hash = None
    user.verification_token_expires_at = None
    db.commit()
    db.refresh(user)
    return user
