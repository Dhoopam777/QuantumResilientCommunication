"""Transactional conversation request lifecycle."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from sqlalchemy.orm import Session, aliased, joinedload

from models.conversation import Conversation
from models.conversation_participant import ConversationParticipant
from models.conversation_request import ConversationRequest
from models.user import User


ACTIVE = "PENDING"
TERMINAL = frozenset({"ACCEPTED", "DECLINED", "CANCELLED"})


def _has_conversation(db: Session, first_id: uuid.UUID, second_id: uuid.UUID) -> bool:
    first = aliased(ConversationParticipant)
    second = aliased(ConversationParticipant)
    return (
        db.query(Conversation.id)
        .join(first, first.conversation_id == Conversation.id)
        .join(second, second.conversation_id == Conversation.id)
        .filter(
            first.user_id == first_id,
            first.left_at.is_(None),
            second.user_id == second_id,
            second.left_at.is_(None),
        )
        .first()
        is not None
    )


def _load_request(db: Session, request_id: uuid.UUID) -> ConversationRequest:
    request = (
        db.query(ConversationRequest)
        .filter(ConversationRequest.id == request_id)
        .with_for_update()
        .first()
    )
    if request is None:
        raise LookupError("Conversation request not found")
    return request


def create_request(db: Session, sender_id: uuid.UUID, username: str) -> ConversationRequest:
    receiver = (
        db.query(User)
        .filter(User.username == username, User.is_active.is_(True))
        .with_for_update()
        .first()
    )
    if receiver is None:
        raise ValueError("Unable to send conversation request")
    if receiver.id == sender_id:
        raise ValueError("Unable to send conversation request")
    if _has_conversation(db, sender_id, receiver.id):
        raise ValueError("Unable to send conversation request")
    existing = (
        db.query(ConversationRequest)
        .filter(
            or_(
                (ConversationRequest.sender_id == sender_id)
                & (ConversationRequest.receiver_id == receiver.id),
                (ConversationRequest.sender_id == receiver.id)
                & (ConversationRequest.receiver_id == sender_id),
            ),
            ConversationRequest.status == ACTIVE,
        )
        .first()
    )
    if existing:
        raise ValueError("Unable to send conversation request")
    request = ConversationRequest(sender_id=sender_id, receiver_id=receiver.id, status=ACTIVE)
    db.add(request)
    try:
        db.commit()
        db.refresh(request)
    except IntegrityError:
        db.rollback()
        raise ValueError("Unable to send conversation request")
    return _load_request(db, request.id)


def list_requests(db: Session, user_id: uuid.UUID, incoming: bool) -> list[ConversationRequest]:
    column = ConversationRequest.receiver_id if incoming else ConversationRequest.sender_id
    query = (
        db.query(ConversationRequest)
        .options(joinedload(ConversationRequest.sender), joinedload(ConversationRequest.receiver))
        .filter(column == user_id)
        .order_by(ConversationRequest.created_at.desc())
    )
    if incoming:
        query = query.filter(ConversationRequest.status == ACTIVE)
    return query.all()


def transition_request(
    db: Session, request_id: uuid.UUID, user_id: uuid.UUID, action: str
) -> tuple[ConversationRequest, Conversation | None]:
    request = _load_request(db, request_id)
    if request.status != ACTIVE:
        raise ValueError("Conversation request is no longer pending")
    if action == "accept" and request.receiver_id != user_id:
        raise PermissionError("Not authorized")
    if action == "decline" and request.receiver_id != user_id:
        raise PermissionError("Not authorized")
    if action == "cancel" and request.sender_id != user_id:
        raise PermissionError("Not authorized")

    conversation = None
    if action == "accept":
        if _has_conversation(db, request.sender_id, request.receiver_id):
            raise ValueError("Conversation already exists")
        conversation = Conversation(
            is_group=False,
            created_by=request.receiver_id,
            is_encrypted=True,
        )
        db.add(conversation)
        db.flush()
        db.add_all([
            ConversationParticipant(
                conversation_id=conversation.id, user_id=request.receiver_id, role="admin"
            ),
            ConversationParticipant(
                conversation_id=conversation.id, user_id=request.sender_id, role="member"
            ),
        ])
        request.status = "ACCEPTED"
    else:
        request.status = {"decline": "DECLINED", "cancel": "CANCELLED"}[action]
    request.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
        db.refresh(request)
        if conversation:
            db.refresh(conversation)
    except IntegrityError:
        db.rollback()
        raise ValueError("Unable to update conversation request")
    return _load_request(db, request.id), conversation
