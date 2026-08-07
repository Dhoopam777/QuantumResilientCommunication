"""Secure group conversation REST API."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.audit_logger import log_group_event
from core.dependencies import require_verified_user
from core.rate_limiter import rate_limiter
from core.websocket_events import (
    WS_EVENT_GROUP_CREATED,
    WS_EVENT_GROUP_UPDATED,
    WS_EVENT_MEMBER_ADDED,
    WS_EVENT_MEMBER_REMOVED,
)
from database.database import get_db
from managers.connection_manager import connection_manager
from models.user import User
from schemas.conversation import (
    ConversationResponse,
    GroupCreate,
    GroupMemberAdd,
    GroupUpdate,
)
from routers.conversation import _build_conversation_response
from services.group_service import add_member, create_group, get_group, remove_member, update_group

router = APIRouter(prefix="/api/v1/groups", tags=["groups"])


def _action_error(
    event: str, group_id: uuid.UUID, user_id: uuid.UUID, reason: str
) -> HTTPException:
    log_group_event(event, str(group_id), str(user_id), reason=reason)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Group action rejected")


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_group_endpoint(
    payload: GroupCreate,
    current_user: User = Depends(require_verified_user),
    db: Session = Depends(get_db),
):
    rate_limiter.check_group_action_rate(str(current_user.id))
    try:
        group = create_group(
            db, current_user.id, payload.group_name, payload.group_description, payload.members
        )
    except ValueError as exc:
        raise _action_error("GROUP_ACTION_REJECTED", uuid.UUID(int=0), current_user.id, str(exc))
    response = _build_conversation_response(db, group)
    event = {"type": WS_EVENT_GROUP_CREATED, "conversation": response.model_dump(mode="json")}
    for participant in group.participants:
        await connection_manager.broadcast_to_user(participant.user_id, event)
        connection_manager.subscribe_user_to_conversation(participant.user_id, group.id)
    log_group_event("GROUP_CREATED", str(group.id), str(current_user.id))
    return response


@router.get("/{group_id}", response_model=ConversationResponse)
def get_group_endpoint(
    group_id: uuid.UUID,
    current_user: User = Depends(require_verified_user),
    db: Session = Depends(get_db),
):
    try:
        group = get_group(db, group_id, current_user.id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Group not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not authorized")
    return _build_conversation_response(db, group)


@router.put("/{group_id}", response_model=ConversationResponse)
async def update_group_endpoint(
    group_id: uuid.UUID,
    payload: GroupUpdate,
    current_user: User = Depends(require_verified_user),
    db: Session = Depends(get_db),
):
    rate_limiter.check_group_action_rate(str(current_user.id))
    try:
        group = update_group(
            db, group_id, current_user.id, payload.group_name,
            payload.group_description, payload.group_avatar_url,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Group not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not authorized")
    except ValueError:
        raise _action_error("GROUP_ACTION_REJECTED", group_id, current_user.id, "update")
    response = _build_conversation_response(db, group)
    await connection_manager.broadcast_to_conversation(
        group.id,
        {"type": WS_EVENT_GROUP_UPDATED, "conversation": response.model_dump(mode="json")},
    )
    log_group_event("GROUP_UPDATED", str(group.id), str(current_user.id))
    return response


@router.post("/{group_id}/members", response_model=ConversationResponse)
async def add_group_member_endpoint(
    group_id: uuid.UUID,
    payload: GroupMemberAdd,
    current_user: User = Depends(require_verified_user),
    db: Session = Depends(get_db),
):
    rate_limiter.check_group_action_rate(str(current_user.id))
    try:
        group, target = add_member(db, group_id, current_user.id, payload.username)
    except LookupError:
        raise HTTPException(status_code=404, detail="Group not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not authorized")
    except ValueError:
        raise _action_error("GROUP_ACTION_REJECTED", group_id, current_user.id, "add_member")
    response = _build_conversation_response(db, group)
    event = {
        "type": WS_EVENT_MEMBER_ADDED,
        "conversation": response.model_dump(mode="json"),
        "member": {"username": target.username, "display_name": target.display_name},
    }
    await connection_manager.broadcast_to_conversation(group.id, event)
    await connection_manager.broadcast_to_user(target.id, event)
    connection_manager.subscribe_user_to_conversation(target.id, group.id)
    log_group_event("MEMBER_ADDED", str(group.id), str(current_user.id), str(target.id))
    return response


@router.delete("/{group_id}/members/{username}", response_model=ConversationResponse)
async def remove_group_member_endpoint(
    group_id: uuid.UUID,
    username: str,
    current_user: User = Depends(require_verified_user),
    db: Session = Depends(get_db),
):
    rate_limiter.check_group_action_rate(str(current_user.id))
    try:
        group, target = remove_member(db, group_id, current_user.id, username)
    except LookupError:
        raise HTTPException(status_code=404, detail="Group not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not authorized")
    except ValueError:
        raise _action_error("GROUP_ACTION_REJECTED", group_id, current_user.id, "remove_member")
    response = _build_conversation_response(db, group)
    event = {
        "type": WS_EVENT_MEMBER_REMOVED,
        "conversation_id": str(group.id),
        "username": target.username,
    }
    await connection_manager.broadcast_to_conversation(group.id, event)
    await connection_manager.broadcast_to_user(target.id, event)
    connection_manager.unsubscribe_user_from_conversation(target.id, group.id)
    log_group_event("MEMBER_REMOVED", str(group.id), str(current_user.id), str(target.id))
    return response
