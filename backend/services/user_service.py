"""
User Service for Quantum-Resilient Communication System

This module provides business logic for user operations.
"""

import uuid

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from models.user import User
from schemas.user import UserCreate, UserUpdate
from core.security import hash_password, verify_password


class UserService:
    """Service class for user-related operations."""
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> User | None:
        """
        Retrieve a user by their email address.
        
        Args:
            db: Database session
            email: Email address to search for
        
        Returns:
            User object if found, None otherwise
        """
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> User | None:
        """
        Retrieve a user by their UUID.

        Args:
            db: Database session
            user_id: User UUID as string

        Returns:
            User object if found, None otherwise
        """
        try:
            uid = uuid.UUID(user_id)
        except (ValueError, AttributeError):
            return None
        return db.query(User).filter(User.id == uid).first()

    @staticmethod
    def get_user_by_username(db: Session, username: str) -> User | None:
        """
        Retrieve a user by their username.
        
        Args:
            db: Database session
            username: Username to search for
        
        Returns:
            User object if found, None otherwise
        """
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def create_user(db: Session, user_create: UserCreate) -> User:
        """
        Create a new user with hashed password.
        
        Args:
            db: Database session
            user_create: UserCreate schema with user data
        
        Returns:
            User: Created user object
        
        Raises:
            ValueError: If username or email already exists
        """
        # Check for duplicate username
        existing_user = UserService.get_user_by_username(db, user_create.username)
        if existing_user:
            raise ValueError(f"Username '{user_create.username}' already exists")
        
        # Check for duplicate email
        existing_email = UserService.get_user_by_email(db, user_create.email)
        if existing_email:
            raise ValueError(f"Email '{user_create.email}' already exists")
        
        # Hash the password
        hashed_password = hash_password(user_create.password)
        
        # Create user object
        db_user = User(
            username=user_create.username,
            email=user_create.email,
            password_hash=hashed_password,
            full_name=user_create.full_name,
            profile_picture_url=user_create.profile_picture_url,
            is_active=user_create.is_active,
            is_verified=False,
            is_email_verified=False,
        )
        
        # Add to database
        db.add(db_user)
        
        try:
            db.commit()
            db.refresh(db_user)
            return db_user
        except IntegrityError as e:
            db.rollback()
            # Re-check for duplicates (race condition handling)
            if "username" in str(e.orig):
                raise ValueError(f"Username '{user_create.username}' already exists")
            elif "email" in str(e.orig):
                raise ValueError(f"Email '{user_create.email}' already exists")
            else:
                raise ValueError("Database integrity error occurred")


    @staticmethod
    def authenticate_user(db: Session, username_or_email: str, password: str) -> User | None:
        """
        Authenticate a user by username or email and password.

        Args:
            db: Database session
            username_or_email: Username or email to authenticate
            password: Plain text password to verify

        Returns:
            User object if authentication succeeds, None otherwise
        """
        # Try to find user by username first, then by email
        user = UserService.get_user_by_username(db, username_or_email)
        if user is None:
            user = UserService.get_user_by_email(db, username_or_email)

        # If user not found, return None
        if user is None:
            return None

        # Verify password
        if not verify_password(password, user.password_hash):
            return None

        return user

    @staticmethod
    def update_profile(db: Session, user_id: uuid.UUID, user_update: UserUpdate) -> User:
        """
        Update the editable profile fields for a user.

        Only applies fields that are explicitly set (not None) in the UserUpdate schema.

        Args:
            db: Database session
            user_id: UUID of the user to update
            user_update: UserUpdate schema with editable fields

        Returns:
            User: The updated user object

        Raises:
            ValueError: If the user is not found
        """
        try:
            uid = uuid.UUID(str(user_id))
        except (ValueError, AttributeError):
            raise ValueError("Invalid user ID")

        user = db.query(User).filter(User.id == uid).first()
        if user is None:
            raise ValueError("User not found")

        # Apply only fields that are explicitly provided (not None)
        update_data = user_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        try:
            db.commit()
            db.refresh(user)
            return user
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def get_public_profile(db: Session, user_id: str) -> User | None:
        """
        Retrieve a user's public profile by their UUID.

        Reuses get_user_by_id — the caller is responsible for serializing
        with UserPublic to exclude sensitive fields.

        Args:
            db: Database session
            user_id: User UUID as string

        Returns:
            User object if found, None otherwise
        """
        return UserService.get_user_by_id(db, user_id)


# Convenience functions for direct usage
def get_user_by_email(db: Session, email: str) -> User | None:
    """Convenience function to get user by email."""
    return UserService.get_user_by_email(db, email)


def get_user_by_id(db: Session, user_id: str) -> User | None:
    """Convenience function to get user by ID."""
    return UserService.get_user_by_id(db, user_id)


def get_user_by_username(db: Session, username: str) -> User | None:
    """Convenience function to get user by username."""
    return UserService.get_user_by_username(db, username)


def create_user(db: Session, user_create: UserCreate) -> User:
    """Convenience function to create a new user."""
    return UserService.create_user(db, user_create)


def authenticate_user(db: Session, username_or_email: str, password: str) -> User | None:
    """Convenience function to authenticate a user."""
    return UserService.authenticate_user(db, username_or_email, password)


def update_profile(db: Session, user_id, user_update: UserUpdate) -> User:
    """Convenience function to update a user's profile."""
    return UserService.update_profile(db, user_id, user_update)


def get_public_profile(db: Session, user_id: str) -> User | None:
    """Convenience function to get a user's public profile."""
    return UserService.get_public_profile(db, user_id)
