"""
Message Router for Quantum-Resilient Communication System

This module provides message endpoints.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from database.database import get_db
from schemas.message import (
    MessageCreate, MessageEdit, MessageDelete, MessageResponse, ReplyPreview,
    ReactionCreate, ReactionSummary, ReactionUser,
)
from services.message_service import (
    send_message,
    edit_message,
    delete_message,
    get_conversation_messages,
)
from core.dependencies import require_verified_user
from core.websocket_events import WS_EVENT_NEW_MESSAGE, WS_EVENT_MESSAGE_EDITED, WS_EVENT_MESSAGE_DELETED
from core.websocket_events import WS_EVENT_REACTION_ADDED, WS_EVENT_REACTION_REMOVED
from core.audit_logger import (
    log_reply_created,
    log_reply_rejected,
    log_message_edited,
    log_message_edit_rejected,
    log_message_deleted,
    log_message_delete_rejected,
    log_reaction_event,
    log_message_signature_event,
)
from core.rate_limiter import rate_limiter
from managers.connection_manager import connection_manager
from models.user import User
from models.message import Message
from models.attachment import Attachment
from core.config import settings
from services.crypto_service import CryptoService
from services.reaction_service import (
    reaction_summaries, toggle_reaction, remove_reaction,
)

router = APIRouter(
    prefix="/api/v1/messages",
    tags=["messages"],
)


def _build_reply_preview(db: Session, message: Message) -> ReplyPreview | None:
    """
    Build a ReplyPreview for a message that has a reply_to_message_id.

    Loads the parent message (including soft-deleted ones) and returns
    a minimal preview for rendering the reply indicator.

    Args:
        db: Database session
        message: The message to build a preview for

    Returns:
        ReplyPreview or None if the message is not a reply
    """
    if not message.reply_to_message_id:
        return None

    parent = db.query(Message).filter(Message.id == message.reply_to_message_id).first()
    if parent is None:
        return None

    return ReplyPreview(
        id=parent.id,
        sender_id=parent.sender_id,
        content_encrypted=parent.content_encrypted,
        message_type=parent.message_type,
        is_deleted=parent.is_deleted,
        created_at=parent.created_at,
    )


def _serialize_message(
    db: Session, message: Message, current_user_id: uuid.UUID | None = None
) -> MessageResponse:
    """
    Serialize a Message to MessageResponse, including reply preview.
    """
    signature_status = "unverified"
    if settings.PQC_ENABLED:
        attachments_metadata = [
            {
                "id": str(attachment.id),
                "original_filename": attachment.original_filename,
                "mime_type": attachment.mime_type,
                "file_size": attachment.file_size,
                "checksum_sha256": attachment.checksum_sha256,
                "width": attachment.width,
                "height": attachment.height,
                "encryption_algorithm": attachment.encryption_algorithm,
                "nonce": attachment.nonce,
                "authentication_tag": attachment.authentication_tag,
                "encrypted_size": attachment.encrypted_size,
            }
            for attachment in db.query(Attachment)
            .filter(Attachment.message_id == message.id, Attachment.is_deleted.is_(False))
            .order_by(Attachment.id.asc())
            .all()
        ]
        if not CryptoService.verify_message(message, message.sender, attachments_metadata):
            log_message_signature_event(
                "MESSAGE_VERIFICATION_FAILED",
                str(message.sender_id),
                str(message.id),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message verification failed",
            )
        signature_status = "verified"
        log_message_signature_event(
            "MESSAGE_VERIFIED",
            str(message.sender_id),
            str(message.id),
        )
    return MessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        sender_id=message.sender_id,
        content_encrypted=message.content_encrypted,
        content_hash=message.content_hash,
        message_type=message.message_type,
        reply_to=message.reply_to,
        reply_to_message_id=message.reply_to_message_id,
        reply_preview=_build_reply_preview(db, message),
        is_edited=message.is_edited,
        edited_at=message.edited_at,
        is_deleted=message.is_deleted,
        deleted_at=message.deleted_at,
        deleted_by=message.deleted_by,
        delete_type=message.delete_type,
        created_at=message.created_at,
        updated_at=message.updated_at,
        reactions=(
            [
                ReactionSummary(
                    emoji=item["emoji"],
                    count=item["count"],
                    reacted_by_me=item["reacted_by_me"],
                    users=[ReactionUser(**user) for user in item["users"]],
                )
                for item in reaction_summaries(message, current_user_id)
            ]
            if current_user_id
            else []
        ),
        signature_status=signature_status,
        encryption_version=message.encryption_version,
        nonce=message.nonce,
        authentication_tag=message.authentication_tag,
        attachments=[
            {
                "id": attachment.id,
                "original_filename": attachment.original_filename,
                "mime_type": attachment.mime_type,
                "file_extension": attachment.file_extension,
                "file_size": attachment.file_size,
                "encryption_algorithm": attachment.encryption_algorithm,
                "nonce": attachment.nonce,
                "authentication_tag": attachment.authentication_tag,
                "encrypted_size": attachment.encrypted_size,
                "created_at": attachment.created_at,
            }
            for attachment in message.attachments
            if not attachment.is_deleted
        ],
    )


@router.post(
    "/",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message",
    description="Send a new message in a conversation. Optionally reply to an existing message.",
    responses={
        201: {"description": "Message sent successfully"},
        400: {"description": "Invalid message data or reply target"},
        401: {"description": "Unauthorized - invalid or missing token"},
        403: {"description": "Forbidden - user is not a participant"},
    },
)
async def send_message_endpoint(
    message_create: MessageCreate,
    current_user: User = Depends(require_verified_user),
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
        HTTPException 400: If message data is invalid or reply target invalid
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
            reply_to_message_id=message_create.reply_to_message_id,
            attachment_ids=message_create.attachment_ids,
            encryption_version=message_create.encryption_version,
            nonce=message_create.nonce,
            authentication_tag=message_create.authentication_tag,
            signature=message_create.signature,
            signature_created_at=message_create.signature_created_at,
        )
        if message.signature:
            log_message_signature_event(
                "MESSAGE_SIGNED", str(current_user.id), str(message.id)
            )

        # Audit log reply creation
        if message.reply_to_message_id:
            log_reply_created(
                str(current_user.id),
                str(message.id),
                str(message.conversation_id),
                str(message.reply_to_message_id),
            )

        # Build the response with reply preview
        response = _serialize_message(db, message, current_user.id)

        # Broadcast the saved message to all connected WebSocket participants
        # of this conversation. The message has already been committed to
        # PostgreSQL by send_message(), so this is a post-persistence broadcast.
        message_data = response.model_dump(mode="json")
        await connection_manager.broadcast_to_conversation(
            message_create.conversation_id,
            {"type": WS_EVENT_NEW_MESSAGE, "message": message_data},
        )

        return response
    except ValueError as e:
        # Audit log rejected replies
        if message_create.reply_to_message_id:
            log_reply_rejected(
                str(current_user.id),
                str(message_create.conversation_id),
                str(e),
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put(
    "/{message_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Edit a message",
    description="Edit the text content of a message. Only the sender can edit their own message.",
    responses={
        200: {"description": "Message edited successfully"},
        400: {"description": "Invalid edit data"},
        401: {"description": "Unauthorized - invalid or missing token"},
        403: {"description": "Forbidden - not the message owner or not a participant"},
        404: {"description": "Message not found"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def edit_message_endpoint(
    message_id: uuid.UUID,
    message_edit: MessageEdit,
    current_user: User = Depends(require_verified_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """
    Edit a message's text content.

    Security model:
    - JWT authentication via get_current_user
    - Ownership verification: only the sender can edit their own message
    - Conversation authorization: user must be an active participant
    - IDOR prevention: message ID is a UUID, ownership checked server-side
    - Never leaks whether a message exists (404 for non-existent, 403 for unauthorized)

    After the edit is committed, a `message_edited` WebSocket event is broadcast
    to all authorized conversation participants so clients update in-place.

    Args:
        message_id: UUID of the message to edit
        message_edit: New content and hash
        current_user: Authenticated user from the dependency
        db: Database session dependency

    Returns:
        MessageResponse: Updated message data

    Raises:
        HTTPException 400: If edit data is invalid
        HTTPException 401: If user is not authenticated
        HTTPException 403: If user is not the owner or not a participant
        HTTPException 404: If message does not exist
        HTTPException 429: If rate limit exceeded
    """
    # Rate limiting — prevent edit abuse
    try:
        rate_limiter.check_edit_rate(str(current_user.id))
    except HTTPException:
        log_message_edit_rejected(
            str(current_user.id), str(message_id), "unknown", "rate_limited"
        )
        raise

    # Load the message to determine conversation_id for audit/broadcast
    message = db.query(Message).filter(Message.id == message_id).first()
    if message is None:
        # Never leak whether a message exists — return generic 404
        log_message_edit_rejected(
            str(current_user.id), str(message_id), "unknown", "not_found"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    conversation_id = message.conversation_id

    try:
        updated = edit_message(
            db=db,
            message_id=message_id,
            user_id=current_user.id,
            content_encrypted=message_edit.content_encrypted,
            content_hash=message_edit.content_hash,
            encryption_version=message_edit.encryption_version,
            nonce=message_edit.nonce,
            authentication_tag=message_edit.authentication_tag,
            signature=message_edit.signature,
            signature_created_at=message_edit.signature_created_at,
        )

        # Audit log successful edit
        log_message_edited(
            str(current_user.id),
            str(updated.id),
            str(updated.conversation_id),
        )

        # Build the response with reply preview
        response = _serialize_message(db, updated, current_user.id)

        # Broadcast the edited message to all connected WebSocket participants
        message_data = response.model_dump(mode="json")
        await connection_manager.broadcast_to_conversation(
            updated.conversation_id,
            {"type": WS_EVENT_MESSAGE_EDITED, "message": message_data},
        )

        return response
    except ValueError as e:
        # Audit log rejected edit
        log_message_edit_rejected(
            str(current_user.id),
            str(message_id),
            str(conversation_id),
            str(e),
        )

        error_detail = str(e)
        # Ownership / authorization failures → 403
        if "own messages" in error_detail or "participant" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_detail,
            )
        # Deleted / system / validation failures → 400
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_detail,
        )


@router.delete(
    "/{message_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a message",
    description="Delete a message. Supports 'me' (hide for requesting user) or 'everyone' (soft-delete for all).",
    responses={
        200: {"description": "Message deleted successfully"},
        400: {"description": "Invalid delete data or message cannot be deleted"},
        401: {"description": "Unauthorized - invalid or missing token"},
        403: {"description": "Forbidden - not the message owner or not a participant"},
        404: {"description": "Message not found"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def delete_message_endpoint(
    message_id: uuid.UUID,
    message_delete: MessageDelete,
    current_user: User = Depends(require_verified_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """
    Delete a message.

    Security model:
    - JWT authentication via get_current_user
    - Conversation authorization: user must be an active participant
    - Ownership verification: "everyone" mode requires the original sender
    - IDOR prevention: message ID is a UUID, ownership checked server-side
    - Cross-conversation requests rejected via participant check
    - Never leaks whether a message exists (404 for non-existent, 403 for unauthorized)

    After the deletion is committed, a `message_deleted` WebSocket event is
    broadcast to all authorized conversation participants so clients update
    in-place without a refresh.

    Args:
        message_id: UUID of the message to delete
        message_delete: Delete mode ('me' or 'everyone')
        current_user: Authenticated user from the dependency
        db: Database session dependency

    Returns:
        MessageResponse: Updated message data

    Raises:
        HTTPException 400: If delete data is invalid or message cannot be deleted
        HTTPException 401: If user is not authenticated
        HTTPException 403: If user is not the owner or not a participant
        HTTPException 404: If message does not exist
        HTTPException 429: If rate limit exceeded
    """
    # Rate limiting — prevent delete abuse
    try:
        rate_limiter.check_delete_rate(str(current_user.id))
    except HTTPException:
        log_message_delete_rejected(
            str(current_user.id), str(message_id), "unknown", "rate_limited"
        )
        raise

    # Load the message to determine conversation_id for audit/broadcast
    message = db.query(Message).filter(Message.id == message_id).first()
    if message is None:
        # Never leak whether a message exists — return generic 404
        log_message_delete_rejected(
            str(current_user.id), str(message_id), "unknown", "not_found"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    conversation_id = message.conversation_id

    try:
        updated = delete_message(
            db=db,
            message_id=message_id,
            user_id=current_user.id,
            mode=message_delete.mode,
        )

        # Audit log successful deletion
        log_message_deleted(
            str(current_user.id),
            str(updated.id),
            str(updated.conversation_id),
            updated.delete_type or message_delete.mode,
        )

        # Build the response with reply preview
        response = _serialize_message(db, updated, current_user.id)

        # Broadcast the deleted message to all connected WebSocket participants
        message_data = response.model_dump(mode="json")
        await connection_manager.broadcast_to_conversation(
            updated.conversation_id,
            {"type": WS_EVENT_MESSAGE_DELETED, "message": message_data},
        )

        return response
    except ValueError as e:
        # Audit log rejected deletion
        log_message_delete_rejected(
            str(current_user.id),
            str(message_id),
            str(conversation_id),
            str(e),
        )

        error_detail = str(e)
        # Ownership / authorization failures → 403
        if "own messages" in error_detail or "participant" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_detail,
            )
        # Deleted / system / validation failures → 400
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_detail,
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
    current_user: User = Depends(require_verified_user),
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
        return [_serialize_message(db, m, current_user.id) for m in messages]
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


async def _broadcast_reaction(
    message: Message, current_user_id: uuid.UUID, added: bool, emoji: str
) -> None:
    """Broadcast only the aggregate state to authorized subscribers."""
    await connection_manager.broadcast_to_conversation(
        message.conversation_id,
        {
            "type": WS_EVENT_REACTION_ADDED if added else WS_EVENT_REACTION_REMOVED,
            "message_id": str(message.id),
            "conversation_id": str(message.conversation_id),
            "emoji": emoji,
            "reactions": reaction_summaries(message, current_user_id),
        },
    )


@router.post(
    "/{message_id}/reactions",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Toggle a message reaction",
)
async def toggle_reaction_endpoint(
    message_id: uuid.UUID,
    reaction: ReactionCreate,
    current_user: User = Depends(require_verified_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    rate_limiter.check_reaction_rate(str(current_user.id))
    try:
        message, added = toggle_reaction(db, message_id, current_user.id, reaction.emoji)
    except LookupError:
        log_reaction_event("REACTION_REJECTED", str(current_user.id), "unknown", str(message_id), reaction.emoji)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    except PermissionError as error:
        log_reaction_event("REACTION_REJECTED", str(current_user.id), "unknown", str(message_id), reaction.emoji)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))
    except ValueError as error:
        log_reaction_event("REACTION_REJECTED", str(current_user.id), "unknown", str(message_id), reaction.emoji)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))

    event = "REACTION_ADDED" if added else "REACTION_REMOVED"
    log_reaction_event(event, str(current_user.id), str(message.conversation_id), str(message.id), reaction.emoji)
    await _broadcast_reaction(message, current_user.id, added, reaction.emoji)
    return _serialize_message(db, message, current_user.id)


@router.delete(
    "/{message_id}/reactions",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove a message reaction",
)
async def remove_reaction_endpoint(
    message_id: uuid.UUID,
    reaction: ReactionCreate,
    current_user: User = Depends(require_verified_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    rate_limiter.check_reaction_rate(str(current_user.id))
    try:
        message = remove_reaction(db, message_id, current_user.id, reaction.emoji)
    except LookupError:
        log_reaction_event("REACTION_REJECTED", str(current_user.id), "unknown", str(message_id), reaction.emoji)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    except PermissionError as error:
        log_reaction_event("REACTION_REJECTED", str(current_user.id), "unknown", str(message_id), reaction.emoji)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))
    except ValueError as error:
        log_reaction_event("REACTION_REJECTED", str(current_user.id), "unknown", str(message_id), reaction.emoji)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))

    log_reaction_event("REACTION_REMOVED", str(current_user.id), str(message.conversation_id), str(message.id), reaction.emoji)
    await _broadcast_reaction(message, current_user.id, False, reaction.emoji)
    return _serialize_message(db, message, current_user.id)