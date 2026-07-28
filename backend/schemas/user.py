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
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None


class UserInDB(UserResponse):
    """
    Schema for user stored in database.
    
    Includes password_hash for internal use only.
    Never return this schema in API responses.
    """
    
    password_hash: str