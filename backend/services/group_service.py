"""Transactional group conversation operations."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.conversation import Conversation
from models.conversation_participant import ConversationParticipant
from models.user import User


def _active_membership(db: Session, conversation_id: uuid.UUID, user_id: uuid.UUID):
    return (
        db.query(ConversationParticipant)
        .filter(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == user_id,
            ConversationParticipant.left_at.is_(None),
        )
        .with_for_update()
        .first()
    )


def _load_group(db: Session, group_id: uuid.UUID) -> Conversation:
    group = (
        db.query(Conversation)
        .filter(Conversation.id == group_id, Conversation.is_group.is_(True))
        .with_for_update()
        .first()
    )
    if group is None:
        raise LookupError("Group not found")
    return group


def _require_owner(db: Session, group_id: uuid.UUID, user_id: uuid.UUID) -> Conversation:
    group = _load_group(db, group_id)
    membership = _active_membership(db, group_id, user_id)
    if membership is None or group.created_by != user_id:
        raise PermissionError("Only the group owner may perform this action")
    return group


def _users_by_username(db: Session, usernames: list[str]) -> list[User]:
    return (
        db.query(User)
        .filter(User.username.in_(usernames), User.is_active.is_(True))
        .with_for_update()
        .all()
    )


def create_group(
    db: Session,
    creator_id: uuid.UUID,
    group_name: str,
    group_description: str | None,
    usernames: list[str],
) -> Conversation:
    creator = db.query(User).filter(User.id == creator_id, User.is_active.is_(True)).first()
    if creator is None or creator.username in usernames:
        raise ValueError("Unable to create group")

    users = _users_by_username(db, usernames)
    if len(users) != len(usernames) or len({user.id for user in users}) != len(usernames):
        raise ValueError("Unable to create group")

    group = Conversation(
        is_group=True,
        group_name=group_name,
        group_description=group_description,
        created_by=creator_id,
        is_encrypted=True,
    )
    db.add(group)
    db.flush()
    db.add(
        ConversationParticipant(
            conversation_id=group.id, user_id=creator_id, role="admin"
        )
    )
    db.add_all(
        ConversationParticipant(
            conversation_id=group.id, user_id=user.id, role="member"
        )
        for user in users
    )
    try:
        db.commit()
        db.refresh(group)
    except IntegrityError:
        db.rollback()
        raise ValueError("Unable to create group")
    return group


def get_group(db: Session, group_id: uuid.UUID, user_id: uuid.UUID) -> Conversation:
    group = db.query(Conversation).filter(
        Conversation.id == group_id, Conversation.is_group.is_(True)
    ).first()
    if group is None:
        raise LookupError("Group not found")
    if _active_membership(db, group_id, user_id) is None:
        raise PermissionError("You are not a member of this group")
    return group


def update_group(
    db: Session,
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    group_name: str | None,
    group_description: str | None,
    group_avatar_url: str | None,
) -> Conversation:
    group = _require_owner(db, group_id, user_id)
    if group_name is not None:
        group.group_name = group_name
    if group_description is not None:
        group.group_description = group_description
    if group_avatar_url is not None:
        group.group_avatar_url = group_avatar_url
    group.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(group)
    return group


def add_member(
    db: Session, group_id: uuid.UUID, acting_user_id: uuid.UUID, username: str
) -> tuple[Conversation, User]:
    group = _require_owner(db, group_id, acting_user_id)
    target = (
        db.query(User)
        .filter(User.username == username, User.is_active.is_(True))
        .with_for_update()
        .first()
    )
    if target is None or target.id == group.created_by:
        raise ValueError("Unable to add member")

    membership = (
        db.query(ConversationParticipant)
        .filter(
            ConversationParticipant.conversation_id == group_id,
            ConversationParticipant.user_id == target.id,
        )
        .with_for_update()
        .first()
    )
    if membership is not None and membership.left_at is None:
        raise ValueError("Unable to add member")
    if membership is None:
        membership = ConversationParticipant(
            conversation_id=group_id, user_id=target.id, role="member"
        )
        db.add(membership)
    else:
        membership.left_at = None
        membership.joined_at = datetime.now(timezone.utc)
    group.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
        db.refresh(group)
    except IntegrityError:
        db.rollback()
        raise ValueError("Unable to add member")
    return group, target


def remove_member(
    db: Session, group_id: uuid.UUID, acting_user_id: uuid.UUID, username: str
) -> tuple[Conversation, User]:
    group = _require_owner(db, group_id, acting_user_id)
    target = db.query(User).filter(User.username == username).first()
    if target is None or target.id == group.created_by:
        raise ValueError("Unable to remove member")
    membership = _active_membership(db, group_id, target.id)
    if membership is None:
        raise ValueError("Unable to remove member")
    membership.left_at = datetime.now(timezone.utc)
    membership.updated_at = datetime.now(timezone.utc)
    group.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(group)
    return group, target
