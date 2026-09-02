"""
User Schemas for Quantum-Resilient Communication System

This module defines Pydantic schemas for User validation and serialization.
"""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict


class UserBase(BaseModel):
    """
    Base User schema with common fields.
    
    Used as a base for other User schemas.
    """
    
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    profile_picture_url: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None
    status_message: Optional[str] = None
    last_seen: Optional[datetime] = None
    is_online: bool = False


class UserCreate(UserBase):
    """
    Schema for creating a new user.
    
    Includes password field for registration.
    """
    
    password: str
    is_active: bool = True
    is_verified: bool = False


class UserResponse(UserBase):
    """
    Schema for user responses.
    
    Never exposes password_hash.
    Includes all public user information.
    """
    
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    is_active: bool
    is_verified: bool
    is_email_verified: bool
    email_verified_at: Optional[datetime] = None
    pq_key_created_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None


class UserUpdate(BaseModel):
    """
    Schema for updating user profile.

    Only editable fields are included. Username, email, and id are NOT editable here.
    """

    display_name: Optional[str] = None
    bio: Optional[str] = None
    profile_picture_url: Optional[str] = None
    status_message: Optional[str] = None


class UserPublic(BaseModel):
    """
    Minimal public profile for other users.

    Excludes email and other sensitive fields.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    display_name: Optional[str] = None
    profile_picture_url: Optional[str] = None
    status_message: Optional[str] = None
    is_online: bool = False
    last_seen: Optional[datetime] = None


class UserLogin(BaseModel):
    """
    Schema for user login.
    
    Accepts either username or email for authentication.
    """
    
    username_or_email: str
    password: str


class ResendVerificationRequest(BaseModel):
    """
    Schema for the public verification email resend request.

    Accepts only the email address — no credentials. The endpoint is public
    so users who lost their original verification email can recover without
    signing in (unverified users are intentionally blocked from login).
    """

    email: EmailStr


class ResendVerificationResponse(BaseModel):
    """
    Generic response for the verification email resend request.

    The message is identical regardless of whether the email belongs to an
    existing account, so callers cannot use this endpoint to enumerate
    registered addresses.
    """

    detail: str


class TokenRefresh(BaseModel):
    """
    Schema for token refresh request.
    
    Accepts a refresh token to generate a new access token.
    """

    refresh_token: str


class TokenResponse(BaseModel):
    """
    Schema for token response.
    
    Returned on successful authentication.
    """
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshResponse(BaseModel):
    """
    Schema for token refresh response.
    
    Returns a new access token.
    """

    access_token: str
    token_type: str = "bearer"


class UserInDB(UserResponse):
    """
    Schema for user stored in database.
    
    Includes password_hash for internal use only.
    Never return this schema in API responses.
    """
    
    password_hash: str
