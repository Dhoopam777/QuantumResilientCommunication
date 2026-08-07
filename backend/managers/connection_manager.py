"""
Connection Manager for WebSocket Real-Time Messaging

This module implements the ``ConnectionManager`` which tracks active WebSocket
connections, manages per-conversation subscriptions, and broadcasts messages
only to authorized participants.

Security model:
  - Connections are accepted but remain *unauthenticated* until the client
    sends a valid JWT via the ``auth`` message.
  - Subscription to a conversation requires both authentication AND a database
    lookup confirming the user is an active participant (``is_participant``).
  - Broadcasts are scoped to the subscription set, so a client can only
    receive messages for conversations they were explicitly authorized for.

IDOR prevention:
  - Conversation IDs never appear in the WebSocket URL (single ``/ws`` endpoint).
  - Every ``join_conversation`` request triggers a fresh database query
    (``is_participant``) — there is no trust based on the client-supplied ID.
  - Even if an attacker guesses a conversation UUID, they cannot subscribe
    without being a verified participant in the database.
"""

import uuid
import logging
from typing import Optional

from fastapi import WebSocket
from sqlalchemy.orm import Session

from core.security import decode_token
from core.websocket_events import (
    WS_EVENT_AUTH_SUCCESS,
    WS_EVENT_AUTH_ERROR,
    WS_EVENT_JOINED_CONVERSATION,
    WS_EVENT_LEFT_CONVERSATION,
    WS_EVENT_NEW_MESSAGE,
    WS_EVENT_ERROR,
    WS_EVENT_PONG,
    WS_CLOSE_AUTH_FAILED,
    WS_CLOSE_FORBIDDEN,
)
from services.user_service import get_user_by_id
from services.conversation_service import is_participant

logger = logging.getLogger(__name__)


class ConnectionInfo:
    """
    Metadata for a single WebSocket connection.

    Attributes:
        websocket: The underlying FastAPI WebSocket object.
        user_id: UUID of the authenticated user (None until authenticated).
        username: Username of the authenticated user (None until authenticated).
        authenticated: Whether the connection has passed JWT validation.
        subscribed_conversations: Set of conversation UUIDs the client is
            subscribed to (and authorized for).
    """

    def __init__(self, websocket: WebSocket) -> None:
        self.websocket: WebSocket = websocket
        self.user_id: Optional[uuid.UUID] = None
        self.username: Optional[str] = None
        self.authenticated: bool = False
        self.subscribed_conversations: set[uuid.UUID] = set()


class ConnectionManager:
    """
    Manages WebSocket connections and conversation subscriptions.

    This is the central hub for real-time messaging. It is designed as a
    singleton (instantiated at module level as ``connection_manager``) so
    that both the WebSocket router and the REST message router can access
    the same instance.

    For horizontal scaling (multiple server instances), this class can be
    replaced with a Redis-backed implementation that uses pub/sub for
    cross-instance broadcasting. The public interface remains the same.
    """

    def __init__(self) -> None:
        # websocket -> connection metadata
        self.active_connections: dict[WebSocket, ConnectionInfo] = {}
        # conversation_id -> set of websockets subscribed to that conversation
        self.conversation_subscriptions: dict[uuid.UUID, set[WebSocket]] = {}

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self, websocket: WebSocket) -> None:
        """
        Accept a new WebSocket connection and register it.

        The connection starts in an *unauthenticated* state. The client
        must send an ``auth`` message with a valid JWT before any other
        action is permitted.
        """
        await websocket.accept()
        self.active_connections[websocket] = ConnectionInfo(websocket)
        logger.info(
            "WebSocket connection accepted. Total active: %d",
            len(self.active_connections),
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """
        Remove a WebSocket connection from all tracking structures.

        Called on ``WebSocketDisconnect`` or any unrecoverable error.
        Ensures the connection is removed from every conversation
        subscription set so it can no longer receive broadcasts.
        """
        info = self.active_connections.pop(websocket, None)
        if info is None:
            return

        # Remove from all conversation subscription sets
        for conv_id in info.subscribed_conversations:
            subs = self.conversation_subscriptions.get(conv_id)
            if subs is not None:
                subs.discard(websocket)
                # Clean up empty sets to avoid memory growth
                if not subs:
                    del self.conversation_subscriptions[conv_id]

        logger.info(
            "WebSocket disconnected. User: %s, Total active: %d",
            info.username or "unauthenticated",
            len(self.active_connections),
        )

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def authenticate(self, websocket: WebSocket, token: str, db: Session) -> Optional[object]:
        """
        Validate a JWT and mark the connection as authenticated.

        Reuses the same ``decode_token`` function as the REST
        ``get_current_user`` dependency, ensuring identical validation:
          - Signature verification (HS256)
          - Expiration check
          - Token type must be "access"
          - User must exist in the database
          - User must be active (``is_active == True``)

        Args:
            websocket: The WebSocket connection to authenticate.
            token: JWT access token string.
            db: SQLAlchemy database session.

        Returns:
            The authenticated ``User`` object, or ``None`` if validation
            fails for any reason.
        """
        try:
            payload = decode_token(token)
        except Exception:
            logger.warning("WebSocket auth failed: invalid or expired token")
            return None

        # Validate token type (same check as get_current_user)
        if payload.get("type") != "access":
            logger.warning("WebSocket auth failed: token type is not 'access'")
            return None

        # Extract user ID from subject
        user_id_str = payload.get("sub")
        if not user_id_str:
            logger.warning("WebSocket auth failed: missing subject in token")
            return None

        # Load user from database
        user = get_user_by_id(db, user_id_str)
        if user is None:
            logger.warning("WebSocket auth failed: user not found (id=%s)", user_id_str)
            return None

        if not user.is_active:
            logger.warning("WebSocket auth failed: inactive user (id=%s)", user_id_str)
            return None

        # Mark the connection as authenticated
        info = self.active_connections.get(websocket)
        if info is not None:
            info.user_id = user.id
            info.username = user.username
            info.authenticated = True

        logger.info("WebSocket authenticated: user=%s", user.username)
        return user

    # ------------------------------------------------------------------
    # Subscription management
    # ------------------------------------------------------------------

    def subscribe(self, websocket: WebSocket, conversation_id: uuid.UUID, db: Session) -> bool:
        """
        Subscribe an authenticated connection to a conversation.

        **Authorization check**: Before subscribing, the server queries the
        database via ``is_participant()`` to verify the authenticated user
        is an active participant (``left_at IS NULL``) in the requested
        conversation. This is the core IDOR prevention mechanism.

        Args:
            websocket: The authenticated WebSocket connection.
            conversation_id: UUID of the conversation to join.
            db: SQLAlchemy database session.

        Returns:
            ``True`` if the subscription was created, ``False`` if the
            user is not authorized (not a participant).
        """
        info = self.active_connections.get(websocket)
        if info is None or not info.authenticated:
            return False

        # Database authorization check — this is what prevents IDOR
        if not is_participant(db, conversation_id, info.user_id):
            logger.warning(
                "Subscription denied: user %s is not a participant in conversation %s",
                info.user_id,
                conversation_id,
            )
            return False

        # Add to subscription sets
        info.subscribed_conversations.add(conversation_id)
        self.conversation_subscriptions.setdefault(conversation_id, set()).add(websocket)

        logger.info(
            "User %s subscribed to conversation %s",
            info.username,
            conversation_id,
        )
        return True

    def unsubscribe(self, websocket: WebSocket, conversation_id: uuid.UUID) -> None:
        """
        Remove a connection from a conversation's subscription set.
        """
        info = self.active_connections.get(websocket)
        if info is not None:
            info.subscribed_conversations.discard(conversation_id)

        subs = self.conversation_subscriptions.get(conversation_id)
        if subs is not None:
            subs.discard(websocket)
            if not subs:
                del self.conversation_subscriptions[conversation_id]

    # ------------------------------------------------------------------
    # Broadcasting
    # ------------------------------------------------------------------

    async def broadcast_to_conversation(self, conversation_id: uuid.UUID, message: dict) -> None:
        """
        Broadcast a message to all subscribers of a conversation.

        Only connections that have been explicitly authorized (via
        ``subscribe``) for this conversation will receive the message.
        Dead connections are detected and cleaned up automatically.

        Args:
            conversation_id: UUID of the conversation to broadcast to.
            message: JSON-serializable dict to send to each subscriber.
        """
        subs = self.conversation_subscriptions.get(conversation_id)
        if not subs:
            return

        # Copy to avoid mutation during iteration
        for ws in list(subs):
            try:
                await ws.send_json(message)
            except Exception:
                # Connection is likely dead — clean it up
                logger.warning("Failed to send to WebSocket, removing from subscriptions")
                self.disconnect(ws)

    async def broadcast_to_user(self, user_id: uuid.UUID, message: dict) -> None:
        """Send an event only to authenticated connections for one user."""
        for ws, info in list(self.active_connections.items()):
            if info.authenticated and info.user_id == user_id:
                try:
                    await ws.send_json(message)
                except Exception:
                    self.disconnect(ws)

    def subscribe_user_to_conversation(self, user_id: uuid.UUID, conversation_id: uuid.UUID) -> None:
        """Subscribe the user's authenticated sockets after an accepted request."""
        for ws, info in list(self.active_connections.items()):
            if info.authenticated and info.user_id == user_id:
                info.subscribed_conversations.add(conversation_id)
                self.conversation_subscriptions.setdefault(conversation_id, set()).add(ws)

    def unsubscribe_user_from_conversation(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> None:
        """Remove a user's authenticated sockets from a conversation."""
        for ws, info in list(self.active_connections.items()):
            if info.authenticated and info.user_id == user_id:
                self.unsubscribe(ws, conversation_id)

    async def send_to_connection(self, websocket: WebSocket, message: dict) -> None:
        """
        Send a message to a single WebSocket connection.

        If the send fails, the connection is cleaned up.
        """
        try:
            await websocket.send_json(message)
        except Exception:
            logger.warning("Failed to send to WebSocket, removing connection")
            self.disconnect(websocket)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def get_connection_info(self, websocket: WebSocket) -> Optional[ConnectionInfo]:
        """Return the ConnectionInfo for a given WebSocket, or None."""
        return self.active_connections.get(websocket)

    def is_authenticated(self, websocket: WebSocket) -> bool:
        """Check whether a WebSocket connection has been authenticated."""
        info = self.active_connections.get(websocket)
        return info is not None and info.authenticated

    def get_subscribed_conversations(self, websocket: WebSocket) -> set[uuid.UUID]:
        """Return the set of conversation IDs a connection is subscribed to."""
        info = self.active_connections.get(websocket)
        if info is None:
            return set()
        return info.subscribed_conversations.copy()

    def get_connection_count(self) -> int:
        """Return the total number of active (connected) WebSockets."""
        return len(self.active_connections)

    def get_subscription_count(self, conversation_id: uuid.UUID) -> int:
        """Return the number of subscribers for a given conversation."""
        return len(self.conversation_subscriptions.get(conversation_id, set()))


# ---------------------------------------------------------------------------
# Global singleton instance
# ---------------------------------------------------------------------------

connection_manager = ConnectionManager()