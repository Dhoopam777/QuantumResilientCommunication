"""Authenticated conversation request and username search endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.audit_logger import log_conversation_request_event
from core.dependencies import require_verified_user
from core.rate_limiter import rate_limiter
from database.database import get_db
from managers.connection_manager import connection_manager
from models.user import User
from schemas.conversation_request import (
    ConversationRequestCreate,
    ConversationRequestResponse,
    RequestUser,
)
from services.conversation_request_service import (
    create_request, list_requests, transition_request,
)

router = APIRouter(prefix="/api/v1/conversation-requests", tags=["conversation requests"])
users_router = APIRouter(prefix="/api/v1/users", tags=["users"])


def _user(user: User) -> RequestUser:
    return RequestUser(
        username=user.username,
        display_name=user.display_name or user.full_name,
        profile_picture_url=user.profile_picture_url,
        status="online" if user.is_online else "offline",
    )


def _response(request) -> ConversationRequestResponse:
    return ConversationRequestResponse(
        id=request.id,
        sender=_user(request.sender),
        receiver=_user(request.receiver),
        status=request.status,
        created_at=request.created_at,
        updated_at=request.updated_at,
    )


@users_router.get("/search")
def search_users(
    q: str = Query(..., min_length=1, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$"),
    current_user: User = Depends(require_verified_user),
    db: Session = Depends(get_db),
) -> list[RequestUser]:
    users = (
        db.query(User)
        .filter(User.username.ilike(f"{q}%"), User.is_active.is_(True), User.id != current_user.id)
        .order_by(User.username)
        .limit(20)
        .all()
    )
    return [_user(user) for user in users]


@router.post("", response_model=ConversationRequestResponse, status_code=status.HTTP_201_CREATED)
async def send_request(
    payload: ConversationRequestCreate,
    current_user: User = Depends(require_verified_user),
    db: Session = Depends(get_db),
):
    rate_limiter.check_conversation_request_rate(str(current_user.id))
    try:
        request = create_request(db, current_user.id, payload.username)
    except ValueError as error:
        log_conversation_request_event("REQUEST_REJECTED", str(current_user.id), "unknown", "unknown", str(error))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to send conversation request")
    log_conversation_request_event("REQUEST_CREATED", str(request.sender_id), str(request.receiver_id), str(request.id))
    await connection_manager.broadcast_to_user(
        request.receiver_id,
        {"type": "conversation_request_received", "request": _response(request).model_dump(mode="json")},
    )
    return _response(request)


@router.get("/incoming", response_model=list[ConversationRequestResponse])
def incoming(current_user: User = Depends(require_verified_user), db: Session = Depends(get_db)):
    return [_response(request) for request in list_requests(db, current_user.id, True)]


@router.get("/outgoing", response_model=list[ConversationRequestResponse])
def outgoing(current_user: User = Depends(require_verified_user), db: Session = Depends(get_db)):
    return [_response(request) for request in list_requests(db, current_user.id, False)]


async def _transition(request_id: uuid.UUID, action: str, current_user: User, db: Session):
    try:
        request, conversation = transition_request(db, request_id, current_user.id, action)
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation request not found")
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    event = {
        "accept": "REQUEST_ACCEPTED",
        "decline": "REQUEST_DECLINED",
        "cancel": "REQUEST_CANCELLED",
    }[action]
    log_conversation_request_event(event, str(request.sender_id), str(request.receiver_id), str(request.id))
    event_type = f"conversation_request_{action}ed" if action != "cancel" else "conversation_request_cancelled"
    event_data = {"type": event_type, "request": _response(request).model_dump(mode="json")}
    await connection_manager.broadcast_to_user(request.sender_id, event_data)
    await connection_manager.broadcast_to_user(request.receiver_id, event_data)
    if conversation:
        connection_manager.subscribe_user_to_conversation(request.sender_id, conversation.id)
        connection_manager.subscribe_user_to_conversation(request.receiver_id, conversation.id)
        conversation_data = {"id": str(conversation.id)}
        await connection_manager.broadcast_to_user(
            request.sender_id, {"type": "conversation_created", "conversation": conversation_data}
        )
        await connection_manager.broadcast_to_user(
            request.receiver_id, {"type": "conversation_created", "conversation": conversation_data}
        )
    return _response(request)


@router.post("/{request_id}/accept", response_model=ConversationRequestResponse)
async def accept_request(request_id: uuid.UUID, current_user: User = Depends(require_verified_user), db: Session = Depends(get_db)):
    return await _transition(request_id, "accept", current_user, db)


@router.post("/{request_id}/decline", response_model=ConversationRequestResponse)
async def decline_request(request_id: uuid.UUID, current_user: User = Depends(require_verified_user), db: Session = Depends(get_db)):
    return await _transition(request_id, "decline", current_user, db)


@router.delete("/{request_id}", response_model=ConversationRequestResponse)
async def cancel_request(request_id: uuid.UUID, current_user: User = Depends(require_verified_user), db: Session = Depends(get_db)):
    return await _transition(request_id, "cancel", current_user, db)
