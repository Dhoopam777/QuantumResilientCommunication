# WebSocket Architecture — QuantumResilientCommunication

## Overview

This document describes the WebSocket-based real-time messaging architecture for the Quantum-Resilient Communication System. The architecture is designed with **security as the highest priority**, ensuring that every connection is authenticated, every subscription is authorized, and no conversation IDs are exposed in URLs.

---

## 1. Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Client (React/Vite)                   │
│  WebSocketClient (web/src/lib/websocket.js)              │
│  → connects to /ws, sends auth + join_conversation       │
└──────────────────────┬──────────────────────────────────┘
                       │ wss:// (proxied via Vite)
┌──────────────────────▼──────────────────────────────────┐
│              FastAPI App (main.py)                       │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  WebSocket Router  (routers/websocket.py)           │ │
│  │  → /ws endpoint (single, no convo ID in URL)        │ │
│  │  → message dispatch loop                            │ │
│  └──────────────┬──────────────────────────────────────┘ │
│                 │                                        │
│  ┌──────────────▼──────────────────────────────────────┐ │
│  │  ConnectionManager  (managers/connection_manager.py) │ │
│  │  → tracks active connections (WebSocket → ConnInfo)│ │
│  │  → tracks conversation subscriptions (conv_id → set)│ │
│  │  → authenticate(), subscribe(), broadcast()         │ │
│  └──────────────┬──────────────────────────────────────┘ │
│                 │                                        │
│  ┌──────────────▼──────────────────────────────────────┐ │
│  │  Auth & Authorization Layer                          │ │
│  │  → core/security.py: decode_token() (reused)        │ │
│  │  → services/user_service.py: get_user_by_id()       │ │
│  │  → services/conversation_service.py: is_participant()│ │
│  └──────────────────────────────────────────────────────┘ │
│                 │                                        │
│  ┌──────────────▼──────────────────────────────────────┐ │
│  │  REST Routers (unchanged)                            │ │
│  │  → routers/message.py: POST /messages               │ │
│  │    → after commit, calls connection_manager         │ │
│  │      .broadcast_to_conversation()                   │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                       │
                       ▼
              PostgreSQL (messages, participants)
```

---

## 2. Security Model

### 2.1 Authentication (JWT)

- The client connects to `/ws` and immediately sends an `auth` message containing the JWT access token:
  ```json
  { "type": "auth", "token": "<jwt-access-token>" }
  ```
- The server calls `decode_token()` (from `core/security.py`) to validate:
  - **Signature verification** (HS256)
  - **Expiration check** (token must not be expired)
  - **Token type** must be `"access"` (refresh tokens are rejected)
  - **User existence** — the user must exist in the database
  - **User activity** — the user must have `is_active == True`
- **The token is never placed in the URL.** It travels inside the encrypted WebSocket frame as a JSON message body, so it does not appear in server access logs, proxy logs, or browser history.

### 2.2 Authorization (Per-Conversation)

- After authentication, the client sends:
  ```json
  { "type": "join_conversation", "conversation_id": "<uuid>" }
  ```
- Before subscribing, the server calls `is_participant(db, conversation_id, user_id)` — the **same function** used by the REST message and conversation routers. This queries the `conversation_participants` table and verifies `left_at IS NULL` (active membership).
- If the user is **not** a participant, the server sends an error and **closes the socket** with code `4403` (Forbidden).
- If the user **is** a participant, the connection is added to that conversation's subscription set.

### 2.3 IDOR Prevention

**IDOR (Insecure Direct Object Reference)** is prevented through multiple layers:

1. **No conversation IDs in the URL.** The WebSocket endpoint is always `/ws`. An attacker cannot enumerate or guess conversation IDs from the URL path or query string.

2. **Mandatory database authorization on every subscription.** When a client sends `join_conversation`, the server **always** queries the database (`is_participant()`) to verify the authenticated user is an active participant (`left_at IS NULL`) in that specific conversation. This check happens **before** the connection is added to any subscription set.

3. **Broadcasts are scoped to authorized subscriptions only.** The `ConnectionManager` maintains a mapping of `conversation_id → set[WebSocket]`. A broadcast to conversation X only iterates over WebSockets that have been explicitly authorized for conversation X. There is no way to receive messages from a conversation you haven't been authorized for.

4. **Authentication is required before any action.** The server rejects any `join_conversation` message from an unauthenticated connection. The JWT is validated using the same `decode_token()` function as the REST APIs.

5. **Connection cleanup on disconnect.** When a WebSocket disconnects, `ConnectionManager.disconnect()` removes it from all subscription sets, ensuring stale connections cannot receive messages.

---

## 3. Message Protocol

### 3.1 Incoming Messages (Client → Server)

| `type` | Required Fields | Description |
|---|---|---|
| `auth` | `token` | Authenticate the connection with a JWT access token |
| `join_conversation` | `conversation_id` | Subscribe to a conversation (requires prior auth) |
| `leave_conversation` | `conversation_id` | Unsubscribe from a conversation |
| `ping` | — | Heartbeat; server responds with `pong` |

### 3.2 Outgoing Messages (Server → Client)

| `type` | Fields | Description |
|---|---|---|
| `auth_success` | `user_id`, `username` | Authentication succeeded |
| `auth_error` | `error` | Authentication failed (socket closed) |
| `joined_conversation` | `conversation_id` | Successfully subscribed |
| `left_conversation` | `conversation_id` | Successfully unsubscribed |
| `new_message` | `message` | New message broadcast to conversation participants |
| `error` | `error`, `code?` | Generic error |
| `pong` | — | Heartbeat response |

---

## 4. Message Flow

### 4.1 Connection & Authentication Flow

```
Client                          Server
  │                                │
  │  WebSocket GET /ws             │
  │ ──────────────────────────────→ │
  │                                │  accept()
  │  ←──────────────────────────── │
  │                                │
  │  {type:"auth", token:"<jwt>"}  │
  │ ──────────────────────────────→ │
  │                                │  decode_token()
  │                                │  get_user_by_id()
  │                                │  check is_active
  │                                │  mark authenticated
  │  {type:"auth_success", ...}    │
  │  ←──────────────────────────── │
  │                                │
  │  {type:"join_conversation",    │
  │   conversation_id:"<uuid>"}    │
  │ ──────────────────────────────→ │
  │                                │  is_participant() ← DB
  │                                │  add to subscription set
  │  {type:"joined_conversation"}  │
  │  ←──────────────────────────── │
  │                                │
  │  (now receives broadcasts)     │
```

### 4.2 Message Broadcast Flow (REST → WebSocket)

```
Client A (sender)                Server                    Client B (recipient)
  │                                │                          │
  │  POST /api/v1/messages/        │                          │
  │  {conversation_id, ...}        │                          │
  │ ──────────────────────────────→ │                          │
  │                                │  send_message() → DB commit
  │                                │  broadcast_to_conversation()
  │                                │ ────────────────────────────→ │
  │                                │  {type:"new_message", ...}   │
  │                                │                          │  render in UI
  │  201 Created                   │                          │
  │  ←──────────────────────────── │                          │
```

The sender also receives the broadcast (confirming delivery). The frontend deduplicates by message ID.

---

## 5. Authorization Flow

```
1. Client → Server: WebSocket connect to /ws
2. Server: accept() connection (unauthenticated)
3. Client → Server: {type:"auth", token:"<jwt>"}
4. Server:
   a. decode_token(token) → validate signature, expiry, type=="access"
   b. get_user_by_id(sub) → load User from DB
   c. check user.is_active
   d. If any step fails → send auth_error, close(4401)
   e. If success → mark connection.authenticated = True, store user_id
5. Client → Server: {type:"join_conversation", conversation_id:"<uuid>"}
6. Server:
   a. Check connection.authenticated (reject if not)
   b. is_participant(db, conversation_id, user_id) → DB query
   c. If not participant → send error, close(4403)
   d. If participant → add WebSocket to conversation's subscription set
7. Client is now authorized to receive broadcasts for that conversation
```

---

## 6. ConnectionManager Design

The `ConnectionManager` is the central hub for real-time messaging. It is designed as a singleton so that both the WebSocket router and the REST message router can access the same instance.

### Key Data Structures

```python
# WebSocket → ConnectionInfo (metadata)
active_connections: dict[WebSocket, ConnectionInfo]

# Conversation ID → set of subscribed WebSockets
conversation_subscriptions: dict[uuid.UUID, set[WebSocket]]
```

### ConnectionInfo

```python
class ConnectionInfo:
    websocket: WebSocket
    user_id: Optional[uuid.UUID]      # None until authenticated
    username: Optional[str]            # None until authenticated
    authenticated: bool                # False until JWT validated
    subscribed_conversations: set[uuid.UUID]  # Conversations joined
```

### Public Interface

| Method | Description |
|---|---|
| `connect(websocket)` | Accept and register a new connection |
| `disconnect(websocket)` | Remove from all tracking structures |
| `authenticate(websocket, token, db)` | Validate JWT, mark authenticated |
| `subscribe(websocket, conversation_id, db)` | Verify participant, add to subscription |
| `unsubscribe(websocket, conversation_id)` | Remove from subscription |
| `broadcast_to_conversation(conversation_id, message)` | Send to all authorized subscribers |
| `send_to_connection(websocket, message)` | Send to a single connection |

---

## 7. File Structure

### New Files

| File | Purpose |
|---|---|
| `backend/core/websocket_events.py` | Event type constants and WebSocket close codes |
| `backend/schemas/websocket.py` | Pydantic schemas for incoming/outgoing WebSocket messages |
| `backend/managers/__init__.py` | Package init exporting `ConnectionManager` |
| `backend/managers/connection_manager.py` | `ConnectionManager` class with authentication, subscription, broadcast |
| `backend/routers/websocket.py` | WebSocket endpoint at `/ws` with message dispatch loop |
| `backend/tests/routers/test_websocket.py` | Tests for auth, join, broadcast, IDOR prevention |
| `web/src/lib/websocket.js` | Frontend `WebSocketClient` class with auto-reconnect, auth, join |
| `docs/design/websocket_architecture.md` | This document |

### Modified Files

| File | Change |
|---|---|
| `backend/main.py` | Added `from routers.websocket import router as websocket_router; app.include_router(websocket_router)` |
| `backend/routers/message.py` | Made `send_message_endpoint` `async def`; added broadcast call after DB commit. **API contract unchanged.** |
| `web/src/pages/ChatWindow.jsx` | Integrated `WebSocketClient`: connect on mount, auth with JWT, join conversation, listen for `new_message`, deduplicate by message ID, cleanup on unmount |
| `web/vite.config.js` | Added `/ws` proxy with `ws: true` to forward WebSocket connections |

### Unchanged Files

- `backend/core/security.py` — reused as-is
- `backend/core/dependencies.py` — reused as-is (REST `get_current_user` unchanged)
- `backend/services/message_service.py` — reused as-is
- `backend/services/conversation_service.py` — reused as-is (`is_participant` reused)
- `backend/models/*` — reused as-is
- `backend/schemas/message.py` — reused as-is
- All existing REST routers and tests — unchanged

---

## 8. Future Extensibility

The architecture is designed to accommodate all future features without structural changes:

| Feature | How It Integrates |
|---|---|
| **Typing indicators** | Add `typing_start`/`typing_stop` event types. `ConnectionManager` already tracks subscriptions, so broadcasting typing events to conversation participants is a one-line addition. |
| **Online/offline presence** | `ConnectionManager.active_connections` already tracks all connections. Add a `user_id → set[WebSocket]` index. On connect/disconnect, broadcast `presence_update` to the user's contacts. |
| **Read receipts** | The `ConversationParticipant` model already has `last_read_message_id` and `last_read_at`. Add a `mark_read` event type that updates these fields and broadcasts `read_receipt` to other participants. |
| **Notifications** | Build on the broadcast mechanism. Add a `notification` event type for system messages, conversation invites, etc. |
| **Post-quantum encryption** | The WebSocket layer is transport-only. Messages are already encrypted client-side (`content_encrypted` field). The PQ crypto layer (ML-KEM, ML-DSA) operates above the transport and is unaffected by the WebSocket implementation. |
| **AI assistant** | Add a special `ai_assistant` participant or a dedicated `ai_message` event type. The AI service can subscribe to conversations and respond via the same broadcast mechanism. |

### Horizontal Scaling (Future)

The current `ConnectionManager` is an in-process singleton. For multi-server deployments, replace it with a Redis-backed implementation:
- Use Redis pub/sub for cross-server message broadcasting
- Use Redis sets for connection tracking
- The `ConnectionManager` interface stays the same; only the storage backend changes

---

## 9. Testing Strategy

### Backend Tests (using FastAPI `TestClient` with `websocket_connect`)

1. **Connection & Auth**
   - Valid JWT → `auth_success` received
   - Invalid JWT → `auth_error` + close(4401)
   - Expired JWT → `auth_error` + close(4401)
   - Refresh token → `auth_error` + close(4401)
   - Missing token → `auth_error` + close(4401)

2. **Authorization (IDOR Prevention)**
   - Participant joins conversation → `joined_conversation`
   - Non-participant joins conversation → error + close(4403)
   - Non-existent conversation → error + close(4403)
   - Unauthenticated user tries `join_conversation` → error + close(4401)

3. **Broadcast Integration**
   - Two clients in same conversation: Client A sends via REST POST, Client B receives `new_message` via WebSocket
   - Client not subscribed to conversation does NOT receive the broadcast

4. **Connection Lifecycle**
   - Disconnect removes connection from subscription sets
   - Connection count is tracked correctly

### Frontend Tests
- WebSocket client connects, authenticates, and joins conversation
- New messages appear in real-time without page refresh
- Reconnection works after disconnect