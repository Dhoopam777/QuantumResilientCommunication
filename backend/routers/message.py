"""
Message Router for Quantum-Resilient Communication System

This module provides message endpoints.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from database.database import get_db
from schemas.message import MessageCreate, MessageResponse
from services.message_service import (
    send_message,
    get_conversation_messages,
)
from core.dependencies import get_current_user
from core.websocket_events import WS_EVENT_NEW_MESSAGE
from managers.connection_manager import connection_manager
from models.user import User

router = APIRouter(
    prefix="/api/v1/messages",
    tags=["messages"],
)


@router.post(
    "/",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message",
    description="Send a new message in a conversation.",
    responses={
        201: {"description": "Message sent successfully"},
        400: {"description": "Invalid message data"},
        401: {"description": "Unauthorized - invalid or missing token"},
        403: {"description": "Forbidden - user is not a participant"},
    },
)
async def send_message_endpoint(
    message_create: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """
    Send a new message in a conversation.

    After the message is successfully stored in PostgreSQL, it is broadcast
    to all connected WebSocket participants of the conversation via the
    ConnectionManager. The REST API contract (request/response schema,
    status codes) is unchanged.

    Args:
        message_create: Message creation data
        current_user: Authenticated user from the dependency
        db: Database session dependency

    Returns:
        MessageResponse: Created message data

    Raises:
        HTTPException 400: If message data is invalid
        HTTPException 401: If user is not authenticated
        HTTPException 403: If user is not a participant
    """
    try:
        message = send_message(
            db=db,
            conversation_id=message_create.conversation_id,
            sender_id=current_user.id,
            content_encrypted=message_create.content_encrypted,
            content_hash=message_create.content_hash,
            message_type=message_create.message_type,
            reply_to=message_create.reply_to,
        )

        # Broadcast the saved message to all connected WebSocket participants
        # of this conversation. The message has already been committed to
        # PostgreSQL by send_message(), so this is a post-persistence broadcast.
        message_data = MessageResponse.model_validate(message).model_dump(mode="json")
        await connection_manager.broadcast_to_conversation(
            message_create.conversation_id,
            {"type": WS_EVENT_NEW_MESSAGE, "message": message_data},
        )

        return MessageResponse.model_validate(message)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/conversation/{conversation_id}",
    response_model=list[MessageResponse],
    status_code=status.HTTP_200_OK,
    summary="Get conversation messages",
    description="Retrieve messages for a conversation with pagination.",
    responses={
        200: {"description": "List of messages"},
        400: {"description": "Invalid pagination parameters"},
        401: {"description": "Unauthorized - invalid or missing token"},
        403: {"description": "Forbidden - user is not a participant"},
    },
)
def get_conversation_messages_endpoint(
    conversation_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=100, description="Number of messages to return (1-100)"),
    offset: int = Query(default=0, ge=0, description="Number of messages to skip"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MessageResponse]:
    """
    Get messages for a conversation with pagination.

    Args:
        conversation_id: UUID of the conversation
        limit: Maximum number of messages to return (1-100, default: 50)
        offset: Number of messages to skip (default: 0)
        current_user: Authenticated user from the dependency
        db: Database session dependency

    Returns:
        List of MessageResponse objects ordered by created_at ASC

    Raises:
        HTTPException 400: If pagination parameters are invalid or user is not a participant
        HTTPException 401: If user is not authenticated
        HTTPException 403: If user is not a participant
    """
    try:
        messages = get_conversation_messages(
            db=db,
            conversation_id=conversation_id,
            user_id=current_user.id,
            limit=limit,
            offset=offset,
        )
        return [MessageResponse.model_validate(m) for m in messages]
    except ValueError as e:
        error_detail = str(e)
        if "not a participant" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_detail,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_detail,
        )
