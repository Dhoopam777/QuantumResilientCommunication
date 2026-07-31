"""
Password Security and JWT Utilities for Quantum-Resilient Communication System

This module provides password hashing/verification and JWT token creation/decoding.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from core.config import settings

# Configure bcrypt context
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Number of bcrypt rounds (higher = more secure but slower)
)


def hash_password(password: str) -> str:
    """
    Hash a plain text password using bcrypt.

    Args:
        password: Plain text password to hash

    Returns:
        str: Bcrypt hashed password

    Example:
        hashed = hash_password("my_secure_password")
    """
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a bcrypt hash.

    Args:
        password: Plain text password to verify
        hashed_password: Bcrypt hashed password to verify against

    Returns:
        bool: True if password matches hash, False otherwise

    Example:
        is_valid = verify_password("my_secure_password", hashed_password)
    """
    return pwd_context.verify(password, hashed_password)


def create_access_token(subject: Any) -> str:
    """
    Create a JWT access token.

    Args:
        subject: The subject of the token (typically user ID as string)

    Returns:
        str: Encoded JWT access token

    Example:
        token = create_access_token(str(user.id))
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "type": "access",
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def create_refresh_token(subject: Any) -> str:
    """
    Create a JWT refresh token.

    Args:
        subject: The subject of the token (typically user ID as string)

    Returns:
        str: Encoded JWT refresh token

    Example:
        token = create_refresh_token(str(user.id))
    """
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "type": "refresh",
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string to decode

    Returns:
        dict: Decoded token payload

    Raises:
        JWTError: If token is invalid or expired

    Example:
        payload = decode_token(token)
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])