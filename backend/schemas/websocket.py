"""
WebSocket Message Schemas for Quantum-Resilient Communication System

This module defines Pydantic schemas for validating incoming and outgoing
WebSocket messages. The schemas use a ``type`` discriminator field to route
messages to the appropriate handler.

The protocol is designed to be extensible: new event types can be added by
extending the ``INCOMING_EVENT_TYPES`` / ``OUTGOING_EVENT_TYPES`` sets in
``core/websocket_events.py`` and adding corresponding schema fields here.
"""

import uuid
from typing import Optional, Literal, Any

from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# Incoming message schemas (client → server)
# ---------------------------------------------------------------------------

class WSIncomingMessage(BaseModel):
    """
    Base schema for all incoming WebSocket messages.

    Every client-to-server message must include a ``type`` field that
    determines how the message is routed. Additional fields are optional
    and validated per-message-type by the router.
    """

    model_config = ConfigDict(extra="forbid")

    type: str = Field(..., description="Message type discriminator")
    token: Optional[str] = Field(None, description="JWT access token (for auth messages)")
    conversation_id: Optional[uuid.UUID] = Field(None, description="Conversation UUID (for join/leave messages)")


class WSAuthMessage(BaseModel):
    """Schema for the ``auth`` message — authenticates the WebSocket connection."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["auth"]
    token: str = Field(..., min_length=1, description="JWT access token")


class WSJoinConversationMessage(BaseModel):
    """Schema for the ``join_conversation`` message — subscribes to a conversation."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["join_conversation"]
    conversation_id: uuid.UUID = Field(..., description="UUID of the conversation to join")


class WSLeaveConversationMessage(BaseModel):
    """Schema for the ``leave_conversation`` message — unsubscribes from a conversation."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["leave_conversation"]
    conversation_id: uuid.UUID = Field(..., description="UUID of the conversation to leave")


class WSPingMessage(BaseModel):
    """Schema for the ``ping`` message — heartbeat."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["ping"]


# ---------------------------------------------------------------------------
# Outgoing message schemas (server → client)
# ---------------------------------------------------------------------------

class WSOutgoingMessage(BaseModel):
    """
    Base schema for all outgoing WebSocket messages.

    Every server-to-client message includes a ``type`` field.
    """

    model_config = ConfigDict(extra="forbid")

    type: str = Field(..., description="Message type discriminator")


class WSAuthSuccessMessage(WSOutgoingMessage):
    """Sent when authentication succeeds."""

    type: Literal["auth_success"] = "auth_success"
    user_id: str = Field(..., description="Authenticated user's UUID as string")
    username: str = Field(..., description="Authenticated user's username")


class WSAuthErrorMessage(WSOutgoingMessage):
    """Sent when authentication fails (socket will be closed)."""

    type: Literal["auth_error"] = "auth_error"
    error: str = Field(..., description="Error description")


class WSJoinedConversationMessage(WSOutgoingMessage):
    """Sent when a client successfully joins a conversation."""

    type: Literal["joined_conversation"] = "joined_conversation"
    conversation_id: str = Field(..., description="Conversation UUID as string")


class WSLeftConversationMessage(WSOutgoingMessage):
    """Sent when a client successfully leaves a conversation."""

    type: Literal["left_conversation"] = "left_conversation"
    conversation_id: str = Field(..., description="Conversation UUID as string")


class WSNewMessageMessage(WSOutgoingMessage):
    """
    Sent when a new message is broadcast to a conversation.

    The ``message`` field contains the full message object (serialized
    from ``MessageResponse``) so the client can render it immediately.
    """

    type: Literal["new_message"] = "new_message"
    message: dict = Field(..., description="Serialized message object")


class WSErrorMessage(WSOutgoingMessage):
    """Sent for non-fatal errors (socket remains open unless specified)."""

    type: Literal["error"] = "error"
    error: str = Field(..., description="Error description")
    code: Optional[str] = Field(None, description="Optional error code")


class WSPongMessage(WSOutgoingMessage):
    """Sent in response to a ``ping`` message."""

    type: Literal["pong"] = "pong"


__all__ = [
    # Incoming
    "WSIncomingMessage",
    "WSAuthMessage",
    "WSJoinConversationMessage",
    "WSLeaveConversationMessage",
    "WSPingMessage",
    # Outgoing
    "WSOutgoingMessage",
    "WSAuthSuccessMessage",
    "WSAuthErrorMessage",
    "WSJoinedConversationMessage",
    "WSLeftConversationMessage",
    "WSNewMessageMessage",
    "WSErrorMessage",
    "WSPongMessage",
]
