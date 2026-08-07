"""Secure message reaction business logic."""

import re
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from models.message import Message
from models.message_reaction import MessageReaction
from services.conversation_service import is_participant


SUPPORTED_EMOJI = frozenset({"👍", "❤️", "😂", "😮", "😢", "🙏", "🔥", "👎"})
MAX_EMOJI_BYTES = 32
_SURROGATE_RE = re.compile(r"[\ud800-\udfff]")


def validate_emoji(emoji: str) -> str:
    """Validate and normalize a supported Unicode emoji without accepting controls."""
    if not isinstance(emoji, str) or not emoji or not emoji.strip():
        raise ValueError("Emoji is required")
    if len(emoji.encode("utf-8")) > MAX_EMOJI_BYTES:
        raise ValueError("Emoji is too large")
    if _SURROGATE_RE.search(emoji) or any(ord(char) < 0x20 for char in emoji):
        raise ValueError("Malformed Unicode emoji")
    if emoji not in SUPPORTED_EMOJI:
        raise ValueError("Unsupported emoji")
    return emoji


def _authorized_message(db: Session, message_id: uuid.UUID, user_id: uuid.UUID) -> Message:
    message = (
        db.query(Message)
        .options(joinedload(Message.reactions).joinedload(MessageReaction.user))
        .filter(Message.id == message_id)
        .first()
    )
    if message is None:
        raise LookupError("Message not found")
    if message.message_type == "system":
        raise ValueError("Cannot react to a system message")
    if message.is_deleted:
        raise ValueError("Cannot react to a deleted message")
    if not is_participant(db, message.conversation_id, user_id):
        raise PermissionError("User is not a participant in this conversation")
    return message


def toggle_reaction(
    db: Session, message_id: uuid.UUID, user_id: uuid.UUID, emoji: str
) -> tuple[Message, bool]:
    """Toggle one user's reaction, with the database unique key as the race guard."""
    emoji = validate_emoji(emoji)
    message = _authorized_message(db, message_id, user_id)
    existing = (
        db.query(MessageReaction)
        .filter(
            MessageReaction.message_id == message_id,
            MessageReaction.user_id == user_id,
            MessageReaction.emoji == emoji,
        )
        .with_for_update()
        .first()
    )
    if existing:
        db.delete(existing)
        added = False
    else:
        db.add(
            MessageReaction(
                message_id=message_id,
                user_id=user_id,
                emoji=emoji,
                created_at=datetime.now(timezone.utc),
            )
        )
        added = True
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # A concurrent insert won the unique key. Treat this request as a
        # toggle removal so duplicate rows can never escape the transaction.
        concurrent = (
            db.query(MessageReaction)
            .filter(
                MessageReaction.message_id == message_id,
                MessageReaction.user_id == user_id,
                MessageReaction.emoji == emoji,
            )
            .first()
        )
        if concurrent:
            db.delete(concurrent)
            db.commit()
            added = False
        else:
            raise
    return _authorized_message(db, message_id, user_id), added


def remove_reaction(
    db: Session, message_id: uuid.UUID, user_id: uuid.UUID, emoji: str
) -> Message:
    """Remove the requesting user's reaction after authorization."""
    emoji = validate_emoji(emoji)
    message = _authorized_message(db, message_id, user_id)
    reaction = (
        db.query(MessageReaction)
        .filter(
            MessageReaction.message_id == message_id,
            MessageReaction.user_id == user_id,
            MessageReaction.emoji == emoji,
        )
        .first()
    )
    if reaction:
        db.delete(reaction)
        db.commit()
    return _authorized_message(db, message_id, user_id)


def reaction_summaries(message: Message, current_user_id: uuid.UUID) -> list[dict]:
    """Aggregate reactions without exposing message content or JWT material."""
    grouped: dict[str, list[MessageReaction]] = defaultdict(list)
    for reaction in message.reactions:
        grouped[reaction.emoji].append(reaction)
    return [
        {
            "emoji": emoji,
            "count": len(items),
            "reacted_by_me": any(item.user_id == current_user_id for item in items),
            "users": [
                {
                    "id": item.user_id,
                    "name": item.user.display_name or item.user.full_name or item.user.username,
                }
                for item in items
            ],
        }
        for emoji, items in grouped.items()
    ]
