"""
WebSocket Router for Quantum-Resilient Communication System

This module provides the single WebSocket endpoint at ``/ws``.

Security design:
  - **Single endpoint**: All WebSocket traffic goes through ``/ws``. No
    conversation IDs, user IDs, or any parameters appear in the URL path
    or query string. This prevents information leakage via URLs, logs,
    and browser history.
  - **JWT authentication**: The client sends a JWT access token as the
    first message (``{"type": "auth", "token": "..."}``). The token is
    validated using the same ``decode_token`` function as the REST APIs.
    The token is never placed in the URL.
  - **Per-conversation authorization**: Before subscribing to a
    conversation, the server queries the database to verify the
    authenticated user is an active participant. This prevents IDOR.

Message protocol:
  Incoming (client -> server):
    - auth:               {type: "auth", token: "<jwt>"}
    - join_conversation:  {type: "join_conversation", conversation_id: "<uuid>"}
    - leave_conversation: {type: "leave_conversation", conversation_id: "<uuid>"}
    - ping:               {type: "ping"}

  Outgoing (server -> client):
    - auth_success:       {type: "auth_success", user_id, username}
    - auth_error:         {type: "auth_error", error}
    - joined_conversation:{type: "joined_conversation", conversation_id}
    - left_conversation:  {type: "left_conversation", conversation_id}
    - new_message:        {type: "new_message", message: {...}}
    - error:              {type: "error", error, code?}
    - pong:               {type: "pong"}
"""

import json
import logging
import uuid as uuid_module

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session

from database.database import get_db
from core.websocket_events import (
    WS_EVENT_AUTH,
    WS_EVENT_JOIN_CONVERSATION,
    WS_EVENT_LEAVE_CONVERSATION,
    WS_EVENT_PING,
    WS_EVENT_AUTH_SUCCESS,
    WS_EVENT_AUTH_ERROR,
    WS_EVENT_JOINED_CONVERSATION,
    WS_EVENT_LEFT_CONVERSATION,
    WS_EVENT_NEW_MESSAGE,
    WS_EVENT_ERROR,
    WS_EVENT_PONG,
    WS_CLOSE_AUTH_FAILED,
    WS_CLOSE_FORBIDDEN,
    WS_CLOSE_MALFORMED,
    WS_CLOSE_SERVER_ERROR,
)
from managers.connection_manager import connection_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    db: Session = Depends(get_db),
) -> None:
    """
    Single WebSocket endpoint for all real-time communication.

    The connection lifecycle:
      1. Connection is accepted (unauthenticated).
      2. Client must send an ``auth`` message with a valid JWT.
      3. After authentication, client can send ``join_conversation``
         to subscribe to a conversation (authorization checked via DB).
      4. Client receives ``new_message`` broadcasts for subscribed
         conversations.
      5. On disconnect, the connection is cleaned up from all subscriptions.

    Args:
        websocket: The WebSocket connection.
        db: Database session (created at connection time, closed on disconnect).
    """
    # Accept the connection and register it
    await connection_manager.connect(websocket)

    try:
        while True:
            # Receive the next message from the client
            raw_data = await websocket.receive_text()

            # Parse JSON
            try:
                message = json.loads(raw_data)
            except (json.JSONDecodeError, TypeError):
                await connection_manager.send_to_connection(websocket, {
                    "type": WS_EVENT_ERROR,
                    "error": "Invalid JSON format",
                    "code": "MALFORMED_JSON",
                })
                continue

            if not isinstance(message, dict):
                await connection_manager.send_to_connection(websocket, {
                    "type": WS_EVENT_ERROR,
                    "error": "Message must be a JSON object",
                    "code": "MALFORMED_MESSAGE",
                })
                continue

            msg_type = message.get("type")

            # ----------------------------------------------------------
            # Auth message - authenticate the connection with a JWT
            # ----------------------------------------------------------
            if msg_type == WS_EVENT_AUTH:
                token = message.get("token")
                if not token or not isinstance(token, str):
                    await connection_manager.send_to_connection(websocket, {
                        "type": WS_EVENT_AUTH_ERROR,
                        "error": "Token is required",
                    })
                    await websocket.close(code=WS_CLOSE_AUTH_FAILED)
                    return

                user = connection_manager.authenticate(websocket, token, db)
                if user is None:
                    await connection_manager.send_to_connection(websocket, {
                        "type": WS_EVENT_AUTH_ERROR,
                        "error": "Invalid or expired token",
                    })
                    await websocket.close(code=WS_CLOSE_AUTH_FAILED)
                    return

                await connection_manager.send_to_connection(websocket, {
                    "type": WS_EVENT_AUTH_SUCCESS,
                    "user_id": str(user.id),
                    "username": user.username,
                })
                continue

            # ----------------------------------------------------------
            # All subsequent messages require authentication
            # ----------------------------------------------------------
            if not connection_manager.is_authenticated(websocket):
                await connection_manager.send_to_connection(websocket, {
                    "type": WS_EVENT_ERROR,
                    "error": "Authentication required. Send an 'auth' message first.",
                    "code": "AUTH_REQUIRED",
                })
                await websocket.close(code=WS_CLOSE_AUTH_FAILED)
                return

            # ----------------------------------------------------------
            # join_conversation - subscribe to a conversation
            # ----------------------------------------------------------
            if msg_type == WS_EVENT_JOIN_CONVERSATION:
                conversation_id_raw = message.get("conversation_id")
                if not conversation_id_raw:
                    await connection_manager.send_to_connection(websocket, {
                        "type": WS_EVENT_ERROR,
                        "error": "conversation_id is required",
                        "code": "MISSING_CONVERSATION_ID",
                    })
                    continue

                # Parse and validate the UUID
                try:
                    conversation_id = uuid_module.UUID(str(conversation_id_raw))
                except (ValueError, AttributeError, TypeError):
                    await connection_manager.send_to_connection(websocket, {
                        "type": WS_EVENT_ERROR,
                        "error": "Invalid conversation_id format",
                        "code": "INVALID_CONVERSATION_ID",
                    })
                    continue

                # Attempt to subscribe (includes DB authorization check)
                success = connection_manager.subscribe(websocket, conversation_id, db)
                if success:
                    await connection_manager.send_to_connection(websocket, {
                        "type": WS_EVENT_JOINED_CONVERSATION,
                        "conversation_id": str(conversation_id),
                    })
                else:
                    # User is not a participant - reject and close
                    await connection_manager.send_to_connection(websocket, {
                        "type": WS_EVENT_ERROR,
                        "error": "You are not a participant in this conversation",
                        "code": "NOT_A_PARTICIPANT",
                    })
                    await websocket.close(code=WS_CLOSE_FORBIDDEN)
                    return
                continue

            # ----------------------------------------------------------
            # leave_conversation - unsubscribe from a conversation
            # ----------------------------------------------------------
            if msg_type == WS_EVENT_LEAVE_CONVERSATION:
                conversation_id_raw = message.get("conversation_id")
                if not conversation_id_raw:
                    await connection_manager.send_to_connection(websocket, {
                        "type": WS_EVENT_ERROR,
                        "error": "conversation_id is required",
                        "code": "MISSING_CONVERSATION_ID",
                    })
                    continue

                try:
                    conversation_id = uuid_module.UUID(str(conversation_id_raw))
                except (ValueError, AttributeError, TypeError):
                    await connection_manager.send_to_connection(websocket, {
                        "type": WS_EVENT_ERROR,
                        "error": "Invalid conversation_id format",
                        "code": "INVALID_CONVERSATION_ID",
                    })
                    continue

                connection_manager.unsubscribe(websocket, conversation_id)
                await connection_manager.send_to_connection(websocket, {
                    "type": WS_EVENT_LEFT_CONVERSATION,
                    "conversation_id": str(conversation_id),
                })
                continue

            # ----------------------------------------------------------
            # ping - heartbeat
            # ----------------------------------------------------------
            if msg_type == WS_EVENT_PING:
                await connection_manager.send_to_connection(websocket, {
                    "type": WS_EVENT_PONG,
                })
                continue

            # ----------------------------------------------------------
            # Unknown message type
            # ----------------------------------------------------------
            await connection_manager.send_to_connection(websocket, {
                "type": WS_EVENT_ERROR,
                "error": f"Unknown message type: {msg_type}",
                "code": "UNKNOWN_MESSAGE_TYPE",
            })

    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
        logger.info("WebSocket disconnected normally")

    except Exception as e:
        logger.exception("Unexpected WebSocket error: %s", e)
        connection_manager.disconnect(websocket)
        try:
            await websocket.close(code=WS_CLOSE_SERVER_ERROR)
        except Exception:
            pass