"""
Authentication Router for Quantum-Resilient Communication System

This module provides user registration, login, token refresh, and protected endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from database.database import get_db
from schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
    TokenResponse,
    TokenRefresh,
    TokenRefreshResponse,
)
from services.user_service import create_user, authenticate_user, update_profile
from core.security import create_access_token, create_refresh_token, decode_token
from core.dependencies import get_current_user
from models.user import User

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["authentication"],
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a new user account with a hashed password.",
    responses={
        201: {"description": "User created successfully"},
        409: {"description": "Username or email already exists"},
    },
)
def register(user_create: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
    """
    Register a new user.

    Args:
        user_create: User registration data (username, email, password, etc.)
        db: Database session dependency

    Returns:
        UserResponse: Created user data (never exposes password_hash)

    Raises:
        HTTPException 409: If username or email already exists
    """
    try:
        user = create_user(db=db, user_create=user_create)
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate a user",
    description="Authenticates a user using username or email and password, returning JWT tokens.",
    responses={
        200: {"description": "Login successful, tokens returned"},
        401: {"description": "Invalid credentials"},
    },
)
def login(user_login: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    """
    Authenticate a user and return JWT tokens.

    Accepts either a username or email along with password.
    Returns access and refresh tokens on success.

    Args:
        user_login: Login credentials (username_or_email, password)
        db: Database session dependency

    Returns:
        TokenResponse: Access and refresh JWT tokens

    Raises:
        HTTPException 401: If credentials are invalid
    """
    user = authenticate_user(
        db=db,
        username_or_email=user_login.username_or_email,
        password=user_login.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate tokens
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Accepts a valid refresh token and returns a new access token.",
    responses={
        200: {"description": "New access token generated"},
        401: {"description": "Invalid or expired refresh token"},
    },
)
def refresh(token_refresh: TokenRefresh, db: Session = Depends(get_db)) -> TokenRefreshResponse:
    """
    Refresh an access token using a valid refresh token.

    Args:
        token_refresh: Refresh token data
        db: Database session dependency

    Returns:
        TokenRefreshResponse: New access token

    Raises:
        HTTPException 401: If the refresh token is invalid or expired
    """
    # Decode the refresh token
    try:
        payload = decode_token(token_refresh.refresh_token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate token type is "refresh"
    token_type = payload.get("type")
    if token_type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Refresh token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user ID from token subject
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate new access token
    new_access_token = create_access_token(subject=user_id)

    return TokenRefreshResponse(
        access_token=new_access_token,
        token_type="bearer",
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Returns the profile of the currently authenticated user. Requires a valid access token.",
    responses={
        200: {"description": "Current user profile"},
        401: {"description": "Unauthorized - invalid or missing token"},
    },
)
def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """
    Get the profile of the currently authenticated user.

    Args:
        current_user: Authenticated user from the dependency

    Returns:
        UserResponse: Current user profile data
    """
    return UserResponse.model_validate(current_user)


@router.put(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update current user profile",
    description="Updates the editable profile fields of the currently authenticated user.",
    responses={
        200: {"description": "Profile updated successfully"},
        401: {"description": "Unauthorized - invalid or missing token"},
        404: {"description": "User not found"},
    },
)
def update_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Update the profile of the currently authenticated user.

    Only editable fields (display_name, bio, profile_picture_url, status_message)
    are updated. Username, email, and id cannot be changed through this endpoint.

    Args:
        user_update: Editable profile fields
        current_user: Authenticated user from the dependency
        db: Database session dependency

    Returns:
        UserResponse: Updated user profile data

    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 404: If user is not found
    """
    try:
        user = update_profile(db=db, user_id=current_user.id, user_update=user_update)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    return UserResponse.model_validate(user)
