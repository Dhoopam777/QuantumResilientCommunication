/**
 * WebSocket client for real-time messaging.
 *
 * Connects to the single /ws endpoint, authenticates with a JWT access
 * token (sent as the first message — never in the URL), and subscribes
 * to conversation broadcasts.
 *
 * Features:
 *   - Auto-reconnect with exponential backoff (stops on auth failure)
 *   - Event listener pattern (on/off/emit)
 *   - Automatic auth on connect
 *   - reconnectWithToken() — re-authenticate after token refresh
 *   - Graceful cleanup on disconnect
 */

const WS_EVENT_AUTH = 'auth'
const WS_EVENT_AUTH_SUCCESS = 'auth_success'
const WS_EVENT_AUTH_ERROR = 'auth_error'
const WS_EVENT_JOIN_CONVERSATION = 'join_conversation'
const WS_EVENT_LEAVE_CONVERSATION = 'leave_conversation'
const WS_EVENT_PING = 'ping'
const WS_EVENT_PONG = 'pong'
const WS_EVENT_NEW_MESSAGE = 'new_message'
const WS_EVENT_MESSAGE_EDITED = 'message_edited'
const WS_EVENT_MESSAGE_DELETED = 'message_deleted'
const WS_EVENT_ERROR = 'error'
const WS_EVENT_JOINED_CONVERSATION = 'joined_conversation'
const WS_EVENT_LEFT_CONVERSATION = 'left_conversation'

const MAX_RECONNECT_ATTEMPTS = 5
const RECONNECT_BASE_DELAY_MS = 1000
const RECONNECT_MAX_DELAY_MS = 5000

export class WebSocketClient {
  constructor() {
    this.ws = null
    this.accessToken = ''
    this.listeners = {}
    this.reconnectAttempts = 0
    this.reconnectTimer = null
    this.connected = false
    this.authenticated = false
    this.authFailure = false // Set to true on auth_error — prevents reconnection
    this.subscribedConversations = new Set()
    this.authFailureCallback = null // Called when auth fails permanently
    this.disposed = false // True after disconnect() — prevents zombie reconnects
    this.connGen = 0 // Incremented on connect()/disconnect() to invalidate stale sockets
  }

  _getWsUrl() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}/ws`
  }

  connect(token) {
    // Supersede any pending reconnect so it cannot open a second socket.
    this._clearReconnectTimer()

    // Bump the generation counter: events from any older socket are ignored,
    // so a superseded connection can never schedule reconnects or mutate state.
    const gen = ++this.connGen
    this.disposed = false

    this.accessToken = token
    this.authenticated = false
    this.authFailure = false
    // Do NOT clear subscribedConversations — they are preserved across
    // reconnects and token refreshes.

    // Close any existing socket before opening a new one so there is never
    // more than one live connection per client.
    if (this.ws) {
      this._closeSocket(this.ws)
      this.ws = null
    }

    const wsUrl = this._getWsUrl()
    const ws = new WebSocket(wsUrl)
    this.ws = ws

    ws.onopen = () => {
      if (gen !== this.connGen || this.disposed) return
      this.connected = true
      this.reconnectAttempts = 0
      this._clearReconnectTimer()
      this.emit('connection_open')
      this._send({ type: WS_EVENT_AUTH, token: this.accessToken })
    }

    ws.onmessage = (event) => {
      if (gen !== this.connGen || this.disposed) return
      let data
      try {
        data = JSON.parse(event.data)
      } catch (e) {
        this.emit('parse_error', event.data)
        return
      }

      const msgType = data.type

      if (msgType === WS_EVENT_AUTH_SUCCESS) {
        this.authenticated = true
        this.authFailure = false
        this.emit('auth_success', data)
        this._rejoinConversations()
        return
      }
      if (msgType === WS_EVENT_AUTH_ERROR) {
        this.authenticated = false
        this.authFailure = true
        this.emit('auth_error', data)
        // Notify the callback that auth failed permanently
        if (this.authFailureCallback) {
          this.authFailureCallback(data)
        }
        return
      }
      if (msgType === WS_EVENT_JOINED_CONVERSATION) {
        this.emit('joined_conversation', data)
        return
      }
      if (msgType === WS_EVENT_LEFT_CONVERSATION) {
        this.emit('left_conversation', data)
        return
      }
      if (msgType === WS_EVENT_PONG) {
        this.emit('pong', data)
        return
      }
      if (msgType === WS_EVENT_ERROR) {
        this.emit('ws_error', data)
        return
      }
      if (msgType === WS_EVENT_NEW_MESSAGE) {
        this.emit('new_message', data)
        return
      }
      if (msgType === WS_EVENT_MESSAGE_EDITED) {
        this.emit('message_edited', data)
        return
      }
      if (msgType === WS_EVENT_MESSAGE_DELETED) {
        this.emit('message_deleted', data)
        return
      }
      this.emit('unknown_message', data)
    }

    ws.onclose = () => {
      // Ignore close events from a socket that has been superseded (stale
      // generation) or torn down intentionally (disconnect).
      if (gen !== this.connGen || this.disposed) return
      this.connected = false
      this.authenticated = false
      this.emit('connection_close')

      // Do NOT reconnect if auth failed (invalid token, expired, etc.)
      if (this.authFailure) {
        return
      }

      // Reconnect with exponential backoff
      if (this.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        this.reconnectAttempts++
        const delay = Math.min(
          RECONNECT_BASE_DELAY_MS * Math.pow(2, this.reconnectAttempts - 1),
          RECONNECT_MAX_DELAY_MS,
        )
        this.reconnectTimer = setTimeout(() => {
          this.connect(this.accessToken)
        }, delay)
      }
    }

    ws.onerror = (error) => {
      if (gen !== this.connGen || this.disposed) return
      this.emit('connection_error', error)
    }
  }

  /**
   * Reconnect with a new access token (after token refresh).
   * Preserves all subscribed conversations so they are re-joined
   * automatically on auth_success.
   * @param {string} newToken - The new JWT access token
   */
  reconnectWithToken(newToken) {
    this.accessToken = newToken
    this.authFailure = false
    this._clearReconnectTimer()
    // Close the current socket cleanly (handlers are detached so its close
    // event cannot schedule a reconnect or mutate state).
    if (this.ws) {
      this._closeSocket(this.ws)
      this.ws = null
    }
    this.connect(newToken)
  }

  /**
   * Register a callback that fires when authentication fails permanently.
   * @param {function} callback - Called with the auth_error data
   */
  setAuthFailureCallback(callback) {
    this.authFailureCallback = callback
  }

  _rejoinConversations() {
    for (const convId of this.subscribedConversations) {
      this._send({ type: WS_EVENT_JOIN_CONVERSATION, conversation_id: convId })
    }
  }

  _send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }

  joinConversation(conversationId) {
    this.subscribedConversations.add(conversationId)
    this._send({ type: WS_EVENT_JOIN_CONVERSATION, conversation_id: conversationId })
  }

  leaveConversation(conversationId) {
    this.subscribedConversations.delete(conversationId)
    this._send({ type: WS_EVENT_LEAVE_CONVERSATION, conversation_id: conversationId })
  }

  ping() {
    this._send({ type: WS_EVENT_PING })
  }

  on(type, callback) {
    if (!this.listeners[type]) {
      this.listeners[type] = []
    }
    this.listeners[type].push(callback)
  }

  off(type, callback) {
    if (!this.listeners[type]) return
    this.listeners[type] = this.listeners[type].filter((cb) => cb !== callback)
  }

  emit(type, data) {
    if (this.listeners[type]) {
      this.listeners[type].forEach((cb) => cb(data))
    }
  }

  _clearReconnectTimer() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  /**
   * Detach all handlers from a socket and close it.
   *
   * Used for intentional teardown so a superseded socket's close event can
   * never reach our callbacks (no state mutation, no reconnect scheduling).
   */
  _closeSocket(socket) {
    if (!socket) return
    socket.onopen = null
    socket.onmessage = null
    socket.onclose = null
    socket.onerror = null
    try {
      socket.close()
    } catch {
      // Already closed or closing — nothing to do
    }
  }

  disconnect() {
    // Mark as intentionally torn down and invalidate any in-flight socket:
    // a close event from it must not schedule a reconnect.
    this.disposed = true
    this.connGen += 1
    this._clearReconnectTimer()
    if (this.ws) {
      this._closeSocket(this.ws)
      this.ws = null
    }
    this.connected = false
    this.authenticated = false
    this.authFailure = false
    this.reconnectAttempts = 0
    this.subscribedConversations.clear()
  }
}

export const WSEvents = {
  AUTH: WS_EVENT_AUTH,
  AUTH_SUCCESS: WS_EVENT_AUTH_SUCCESS,
  AUTH_ERROR: WS_EVENT_AUTH_ERROR,
  JOIN_CONVERSATION: WS_EVENT_JOIN_CONVERSATION,
  LEAVE_CONVERSATION: WS_EVENT_LEAVE_CONVERSATION,
  PING: WS_EVENT_PING,
  PONG: WS_EVENT_PONG,
  NEW_MESSAGE: WS_EVENT_NEW_MESSAGE,
  MESSAGE_EDITED: WS_EVENT_MESSAGE_EDITED,
  MESSAGE_DELETED: WS_EVENT_MESSAGE_DELETED,
  ERROR: WS_EVENT_ERROR,
  JOINED_CONVERSATION: WS_EVENT_JOINED_CONVERSATION,
  LEFT_CONVERSATION: WS_EVENT_LEFT_CONVERSATION,
}