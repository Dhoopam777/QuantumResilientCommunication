"""
WebSocket Event Types and Close Codes for Quantum-Resilient Communication System

This module defines the event type constants and custom close codes used in the
WebSocket message protocol. Centralizing these constants ensures consistency
across the server and client, and makes it trivial to add new event types
(typing indicators, presence, read receipts, etc.) in the future.
"""

# ---------------------------------------------------------------------------
# Incoming message types (client → server)
# ---------------------------------------------------------------------------

WS_EVENT_AUTH = "auth"
WS_EVENT_JOIN_CONVERSATION = "join_conversation"
WS_EVENT_LEAVE_CONVERSATION = "leave_conversation"
WS_EVENT_PING = "ping"

# Future event types (not yet implemented) — reserved for extensibility:
# WS_EVENT_TYPING_START = "typing_start"
# WS_EVENT_TYPING_STOP = "typing_stop"
# WS_EVENT_MARK_READ = "mark_read"
# WS_EVENT_SEND_MESSAGE = "send_message"  # future: send via WS instead of REST

# ---------------------------------------------------------------------------
# Outgoing message types (server → client)
# ---------------------------------------------------------------------------

WS_EVENT_AUTH_SUCCESS = "auth_success"
WS_EVENT_AUTH_ERROR = "auth_error"
WS_EVENT_JOINED_CONVERSATION = "joined_conversation"
WS_EVENT_LEFT_CONVERSATION = "left_conversation"
WS_EVENT_NEW_MESSAGE = "new_message"
WS_EVENT_MESSAGE_EDITED = "message_edited"
WS_EVENT_ERROR = "error"
WS_EVENT_PONG = "pong"

# Future event types (not yet implemented):
# WS_EVENT_MESSAGE_SENT = "message_sent"
# WS_EVENT_TYPING_INDICATOR = "typing_indicator"
# WS_EVENT_READ_RECEIPT = "read_receipt"
# WS_EVENT_PRESENCE_UPDATE = "presence_update"
# WS_EVENT_MESSAGE_DELETED = "message_deleted"

# ---------------------------------------------------------------------------
# Custom WebSocket close codes
# ---------------------------------------------------------------------------

# 4xxx range is reserved for application-defined close codes (per RFC 6455).
WS_CLOSE_AUTH_FAILED = 4401       # Authentication required or failed
WS_CLOSE_FORBIDDEN = 4403         # Authenticated but not authorized
WS_CLOSE_MALFORMED = 4400         # Malformed message / protocol violation
WS_CLOSE_SERVER_ERROR = 4405      # Internal server error

# ---------------------------------------------------------------------------
# Convenience sets for validation
# ---------------------------------------------------------------------------

INCOMING_EVENT_TYPES = frozenset({
    WS_EVENT_AUTH,
    WS_EVENT_JOIN_CONVERSATION,
    WS_EVENT_LEAVE_CONVERSATION,
    WS_EVENT_PING,
})

OUTGOING_EVENT_TYPES = frozenset({
    WS_EVENT_AUTH_SUCCESS,
    WS_EVENT_AUTH_ERROR,
    WS_EVENT_JOINED_CONVERSATION,
    WS_EVENT_LEFT_CONVERSATION,
    WS_EVENT_NEW_MESSAGE,
    WS_EVENT_MESSAGE_EDITED,
    WS_EVENT_ERROR,
    WS_EVENT_PONG,
})

__all__ = [
    # Incoming
    "WS_EVENT_AUTH",
    "WS_EVENT_JOIN_CONVERSATION",
    "WS_EVENT_LEAVE_CONVERSATION",
    "WS_EVENT_PING",
    # Outgoing
    "WS_EVENT_AUTH_SUCCESS",
    "WS_EVENT_AUTH_ERROR",
    "WS_EVENT_JOINED_CONVERSATION",
    "WS_EVENT_LEFT_CONVERSATION",
    "WS_EVENT_NEW_MESSAGE",
    "WS_EVENT_MESSAGE_EDITED",
    "WS_EVENT_ERROR",
    "WS_EVENT_PONG",
    # Close codes
    "WS_CLOSE_AUTH_FAILED",
    "WS_CLOSE_FORBIDDEN",
    "WS_CLOSE_MALFORMED",
    "WS_CLOSE_SERVER_ERROR",
    # Validation sets
    "INCOMING_EVENT_TYPES",
    "OUTGOING_EVENT_TYPES",
]
