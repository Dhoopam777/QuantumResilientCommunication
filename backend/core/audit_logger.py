"""
Audit Logger for Security Events

Logs security-relevant events for compliance and monitoring.
NEVER logs: JWTs, file contents, absolute storage paths.
"""

import logging
import uuid

# Dedicated logger for security events
logger = logging.getLogger("qrc.security")
logger.setLevel(logging.INFO)


def log_upload_success(user_id: str, attachment_id: str, conversation_id: str,
                       filename: str, file_size: int) -> None:
    """Log successful attachment upload."""
    logger.info(
        "ATTACHMENT_UPLOAD_SUCCESS | user=%s attachment=%s conversation=%s "
        "filename=%s size=%d",
        _safe_id(user_id), _safe_id(attachment_id), _safe_id(conversation_id),
        _safe_filename(filename), file_size,
    )


def log_upload_failure(user_id: str, conversation_id: str, reason: str) -> None:
    """Log failed attachment upload."""
    logger.warning(
        "ATTACHMENT_UPLOAD_FAILURE | user=%s conversation=%s reason=%s",
        _safe_id(user_id), _safe_id(conversation_id), reason,
    )


def log_auth_failure(user_id: str, action: str, attachment_id: str) -> None:
    """Log authorization failure (IDOR attempt)."""
    logger.warning(
        "ATTACHMENT_AUTH_FAILURE | user=%s action=%s attachment=%s",
        _safe_id(user_id), action, _safe_id(attachment_id),
    )


def log_invalid_mime(user_id: str, declared_mime: str, detected_mime: str) -> None:
    """Log MIME type mismatch."""
    logger.warning(
        "ATTACHMENT_MIME_MISMATCH | user=%s declared=%s detected=%s",
        _safe_id(user_id), declared_mime, detected_mime,
    )


def log_oversized_upload(user_id: str, size: int) -> None:
    """Log oversized upload attempt."""
    logger.warning(
        "ATTACHMENT_OVERSIZED | user=%s size=%d",
        _safe_id(user_id), size,
    )


def log_rate_limited(user_id: str, action: str) -> None:
    """Log rate-limited request."""
    logger.warning(
        "ATTACHMENT_RATE_LIMITED | user=%s action=%s",
        _safe_id(user_id), action,
    )


def log_reply_created(user_id: str, message_id: str, conversation_id: str,
                      reply_to_message_id: str) -> None:
    """Log a message reply creation."""
    logger.info(
        "MESSAGE_REPLY_CREATED | user=%s message=%s conversation=%s reply_to=%s",
        _safe_id(user_id), _safe_id(message_id), _safe_id(conversation_id),
        _safe_id(reply_to_message_id),
    )


def log_reply_rejected(user_id: str, conversation_id: str, reason: str) -> None:
    """Log a rejected reply (invalid target, cross-conversation, etc.)."""
    logger.warning(
        "MESSAGE_REPLY_REJECTED | user=%s conversation=%s reason=%s",
        _safe_id(user_id), _safe_id(conversation_id), reason,
    )


def log_message_edited(user_id: str, message_id: str, conversation_id: str) -> None:
    """Log a successful message edit. Never logs message contents."""
    logger.info(
        "MESSAGE_EDITED | user=%s message=%s conversation=%s",
        _safe_id(user_id), _safe_id(message_id), _safe_id(conversation_id),
    )


def log_message_edit_rejected(
    user_id: str, message_id: str, conversation_id: str, reason: str
) -> None:
    """Log a rejected message edit. Never logs message contents."""
    logger.warning(
        "MESSAGE_EDIT_REJECTED | user=%s message=%s conversation=%s reason=%s",
        _safe_id(user_id), _safe_id(message_id), _safe_id(conversation_id), reason,
    )


def log_message_deleted(
    user_id: str, message_id: str, conversation_id: str, delete_mode: str
) -> None:
    """Log a successful message deletion. Never logs message contents."""
    logger.info(
        "MESSAGE_DELETED | user=%s message=%s conversation=%s mode=%s",
        _safe_id(user_id), _safe_id(message_id), _safe_id(conversation_id), delete_mode,
    )


def log_message_delete_rejected(
    user_id: str, message_id: str, conversation_id: str, reason: str
) -> None:
    """Log a rejected message deletion. Never logs message contents."""
    logger.warning(
        "MESSAGE_DELETE_REJECTED | user=%s message=%s conversation=%s reason=%s",
        _safe_id(user_id), _safe_id(message_id), _safe_id(conversation_id), reason,
    )


def log_reaction_event(
    event: str, user_id: str, conversation_id: str, message_id: str, emoji: str
) -> None:
    """Log reaction security events without message contents or credentials."""
    logger.info(
        "%s | user=%s conversation=%s message=%s emoji=%s",
        event,
        _safe_id(user_id),
        _safe_id(conversation_id),
        _safe_id(message_id),
        emoji[:32],
    )


def _safe_id(value: str) -> str:
    """Sanitize UUID string for logging — only logs first 8 chars."""
    if value and len(str(value)) >= 8:
        return str(value)[:8]
    return "unknown"


def _safe_filename(filename: str) -> str:
    """Sanitize filename for logging — remove path components."""
    if not filename:
        return "unknown"
    # Only log the basename, never path components
    safe = str(filename).replace("/", "_").replace("\\", "_")
    return safe[:50]