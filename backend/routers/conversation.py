"""
Conversation Router for Quantum-Resilient Communication System

This module provides conversation endpoints.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.database import get_db
from schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationParticipantInfo,
    MessagePreview,
)
from services.conversation_service import (
    create_conversation,
    get_user_conversations,
    get_conversation_by_id,
    is_participant,
    get_conversation_participants,
    get_last_message,
)
from core.dependencies import get_current_user
from models.user import User


def _build_conversation_response(db, conversation) -> ConversationResponse:
    """Build an enhanced ConversationResponse with participants and last message."""
    # Fetch participants with user info
    participant_rows = get_conversation_participants(db=db, conversation_id=conversation.id)
    participants = [
        ConversationParticipantInfo(
            id=cp.id,
            user_id=cp.user_id,
            username=u.username,
            display_name=u.display_name,
            profile_picture_url=u.profile_picture_url,
            is_online=u.is_online,
            last_seen=u.last_seen,
            role=cp.role,
        )
        for cp, u in participant_rows
    ]

    # Fetch last message
    last_msg = get_last_message(db=db, conversation_id=conversation.id)
    last_message = None
    if last_msg:
        last_message = MessagePreview(
            id=last_msg.id,
            sender_id=last_msg.sender_id,
            content_encrypted=last_msg.content_encrypted,
            message_type=last_msg.message_type,
            created_at=last_msg.created_at,
        )

    return ConversationResponse(
        id=conversation.id,
        is_group=conversation.is_group,
        group_name=conversation.group_name,
        group_description=conversation.group_description,
        group_avatar_url=conversation.group_avatar_url,
        created_by=conversation.created_by,
        is_encrypted=conversation.is_encrypted,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        participants=participants,
        last_message=last_message,
    )

router = APIRouter(
    prefix="/api/v1/conversations",
    tags=["conversations"],
)


@router.post(
    "/",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation",
    description="Creates a new conversation with the specified participants.",
    responses={
        201: {"description": "Conversation created successfully"},
        401: {"description": "Unauthorized - invalid or missing token"},
    },
)
def create_conversation_endpoint(
    conversation_create: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationResponse:
    """
    Create a new conversation.

    The current authenticated user is automatically included as a participant
    and receives the 'admin' role.

    Args:
        conversation_create: Conversation creation data
        current_user: Authenticated user from the dependency
        db: Database session dependency

    Returns:
        ConversationResponse: Created conversation data

    Raises:
        HTTPException 401: If user is not authenticated
    """
    conversation = create_conversation(
        db=db,
        creator_id=current_user.id,
        participant_ids=conversation_create.participant_ids,
        is_group=conversation_create.is_group,
        group_name=conversation_create.group_name,
    )
    return _build_conversation_response(db, conversation)


@router.get(
    "/",
    response_model=list[ConversationResponse],
    status_code=status.HTTP_200_OK,
    summary="Get current user's conversations",
    description="Returns all active conversations for the current user.",
    responses={
        200: {"description": "List of conversations"},
        401: {"description": "Unauthorized - invalid or missing token"},
    },
)
def get_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ConversationResponse]:
    """
    Get all active conversations for the current user.

    Args:
        current_user: Authenticated user from the dependency
        db: Database session dependency

    Returns:
        List of ConversationResponse objects ordered by updated_at DESC

    Raises:
        HTTPException 401: If user is not authenticated
    """
    conversations = get_user_conversations(db=db, user_id=current_user.id)
    return [_build_conversation_response(db, c) for c in conversations]


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get conversation by ID",
    description="Returns a specific conversation if the user is a participant.",
    responses={
        200: {"description": "Conversation data"},
        401: {"description": "Unauthorized - invalid or missing token"},
        403: {"description": "Forbidden - user is not a participant"},
        404: {"description": "Conversation not found"},
    },
)
def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationResponse:
    """
    Get a specific conversation by ID.

    Verifies that the current user is an active participant.

    Args:
        conversation_id: UUID of the conversation
        current_user: Authenticated user from the dependency
        db: Database session dependency

    Returns:
        ConversationResponse: Conversation data

    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 403: If user is not a participant
        HTTPException 404: If conversation doesn't exist
    """
    # Check if conversation exists
    conversation = get_conversation_by_id(db=db, conversation_id=conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    # Verify user is a participant
    if not is_participant(db=db, conversation_id=conversation_id, user_id=current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this conversation",
        )

    return _build_conversation_response(db, conversation)
