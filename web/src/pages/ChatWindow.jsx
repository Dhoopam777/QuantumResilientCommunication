import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  conversationApi,
  messageApi,
  getAccessToken,
  getLastConversationId,
  setLastConversationId,
} from '../lib/api'
import { WebSocketClient } from '../lib/websocket'
import { useAuth } from '../context/AuthContext'
import DebugPanel from '../components/DebugPanel'

export default function ChatWindow() {
  const { conversationId } = useParams()
  const navigate = useNavigate()
  const { isLoggedIn, user, accessToken, registerWebSocket, unregisterWebSocket } = useAuth()
  const [conversation, setConversation] = useState({ response: null, error: null, status: null })
  const [messages, setMessages] = useState({ response: null, error: null, status: null })
  const [sendResult, setSendResult] = useState({ request: null, response: null, error: null, status: null })
  const [content, setContent] = useState('')
  const [messageType, setMessageType] = useState('text')
  const [wsStatus, setWsStatus] = useState('disconnected')
  const [wsMessages, setWsMessages] = useState([])
  const wsClientRef = useRef(null)
  // Track message IDs we've already seen to prevent duplicates from any source
  const seenMessageIdsRef = useRef(new Set())
  // Track the token used to connect the WebSocket
  const wsTokenRef = useRef('')

  const fetchConversation = useCallback(async () => {
    const res = await conversationApi.get(conversationId)
    setConversation({
      response: res.data,
      error: res.error || (res.status >= 400 ? JSON.stringify(res.data) : null),
      status: res.status,
    })
  }, [conversationId])

  const fetchMessages = useCallback(async () => {
    const res = await messageApi.list(conversationId)
    setMessages({
      response: res.data,
      error: res.error || (res.status >= 400 ? JSON.stringify(res.data) : null),
      status: res.status,
    })
  }, [conversationId])

  // Persist the selected conversation for restore after page refresh
  useEffect(() => {
    if (conversationId) {
      setLastConversationId(conversationId)
    }
  }, [conversationId])

  // If no conversationId in URL but we have a persisted one, restore it
  useEffect(() => {
    if (isLoggedIn && !conversationId) {
      const lastId = getLastConversationId()
      if (lastId) {
        navigate(`/test/conversations/${lastId}`, { replace: true })
      }
    }
  }, [isLoggedIn, conversationId, navigate])

  // Set up WebSocket connection for real-time messaging
  useEffect(() => {
    if (!isLoggedIn || !conversationId) return

    const token = accessToken || getAccessToken()
    if (!token) return

    const wsClient = new WebSocketClient()
    wsClientRef.current = wsClient
    wsTokenRef.current = token
    // Register with AuthContext so logout can close the WebSocket
    registerWebSocket(wsClient)

    wsClient.on('new_message', (data) => {
      const msg = data.message
      if (!msg || !msg.id) return

      // Single source of truth: use a Set of seen message IDs
      // to prevent duplicates from any source (WebSocket, REST, etc.)
      if (!seenMessageIdsRef.current.has(msg.id)) {
        seenMessageIdsRef.current.add(msg.id)
        setWsMessages((prev) => [...prev, msg])
      }
    })

    wsClient.on('auth_success', () => {
      setWsStatus('connected')
      // joinConversation will be called for all previously subscribed
      // conversations automatically by the client's _rejoinConversations().
      // Explicitly join the current conversation as well.
      wsClient.joinConversation(conversationId)
    })

    wsClient.on('auth_error', () => {
      setWsStatus('auth_failed')
      // Do NOT reconnect — authFailure flag in the client prevents it.
      // The auth_failure_callback could trigger a token refresh here,
      // but api.js handles that on REST calls. For WebSocket, show status.
    })

    wsClient.on('connection_close', () => {
      setWsStatus('disconnected')
    })

    wsClient.on('connection_open', () => {
      setWsStatus('connecting')
    })

    // Register a callback for permanent auth failure
    wsClient.setAuthFailureCallback(() => {
      setWsStatus('auth_failed')
    })

    wsClient.connect(token)

    return () => {
      wsClient.disconnect()
      wsClientRef.current = null
      unregisterWebSocket()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoggedIn, conversationId, registerWebSocket, unregisterWebSocket])

  // Reconnect WebSocket when the access token changes (token refresh)
  useEffect(() => {
    const wsClient = wsClientRef.current
    const token = accessToken || getAccessToken()

    // Only reconnect if we have a WebSocket and the token actually changed
    if (wsClient && token && token !== wsTokenRef.current) {
      wsTokenRef.current = token
      wsClient.reconnectWithToken(token)
    }
  }, [accessToken])

  // Fetch conversation and messages on mount
  useEffect(() => {
    if (isLoggedIn && conversationId) {
      fetchConversation()
      fetchMessages()
    }
  }, [isLoggedIn, conversationId, fetchConversation, fetchMessages])

  // When REST messages are loaded, add their IDs to the seen set
  // so WebSocket broadcasts don't re-add them
  useEffect(() => {
    const msgList = messages.response
    if (messages.status === 200 && Array.isArray(msgList)) {
      msgList.forEach((m) => {
        if (m.id) seenMessageIdsRef.current.add(m.id)
      })
    }
  }, [messages])

  const handleSend = async (e) => {
    e.preventDefault()
    const payload = {
      conversation_id: conversationId,
      content_encrypted: content,
      content_hash: btoa(content).slice(0, 32),
      message_type: messageType,
      reply_to: null,
    }
    setSendResult({ request: payload, response: null, error: null, status: null })
    const res = await messageApi.send(payload)
    setSendResult({
      request: payload,
      response: res.data,
      error: res.error || (res.status >= 400 ? JSON.stringify(res.data) : null),
      status: res.status,
    })
    if (res.status === 201) {
      setContent('')
      // Do NOT call fetchMessages() here. The WebSocket broadcast
      // (new_message event) is the single source of truth for new
      // messages. It delivers the message to ALL participants
      // including the sender, ensuring exactly one render per user.
      // The REST response is only used for error checking.
    }
  }

  if (!isLoggedIn) {
    return <p className="text-gray-500">Please log in first.</p>
  }

  // If we don't have a conversationId yet (restore in progress), show a message
  if (!conversationId) {
    return <p className="text-gray-500">Restoring conversation...</p>
  }

  const msgList = messages.status === 200 && Array.isArray(messages.response) ? messages.response : []

  // Merge REST-fetched messages with WebSocket-received messages.
  // The seenMessageIdsRef ensures no duplicates across both sources.
  const allMessages = (() => {
    const restIds = new Set(msgList.map((m) => m.id))
    const wsOnly = wsMessages.filter((m) => !restIds.has(m.id))
    return [...msgList, ...wsOnly]
  })()

  // Determine the "other" participant for 1:1 conversations, or group info
  const convData = conversation.status === 200 ? conversation.response : null
  const otherParticipant = convData && !convData.is_group
    ? convData.participants?.find((p) => p.user_id !== user?.id)
    : null
  const headerTitle = convData?.is_group
    ? convData.group_name || 'Group'
    : otherParticipant?.display_name || otherParticipant?.username || 'Direct Message'
  const headerSubtitle = otherParticipant ? `@${otherParticipant.username}` : ''
  const isOnline = otherParticipant?.is_online || false
  const statusMessage = otherParticipant?.status_message || ''
  const avatarUrl = otherParticipant?.profile_picture_url
  const headerInitials = (headerTitle)
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
  const participantCount = convData?.participants?.length || 0

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">Chat Window</h2>
        <Link to="/test/conversations" className="text-sm text-blue-600 hover:underline">Back to list</Link>
      </div>

      {/* WebSocket status indicator */}
      <div className="mb-2">
        <span className={`text-xs px-2 py-1 rounded ${
          wsStatus === 'connected' ? 'bg-green-100 text-green-800' :
          wsStatus === 'connecting' ? 'bg-yellow-100 text-yellow-800' :
          wsStatus === 'auth_failed' ? 'bg-red-100 text-red-800' :
          'bg-gray-100 text-gray-800'
        }`}>
          WebSocket: {wsStatus}
        </span>
      </div>

      {/* Chat header with participant profile */}
      <div className="bg-white border rounded p-3 mb-4 flex items-center gap-3">
        {avatarUrl ? (
          <img
            src={avatarUrl}
            alt={headerTitle}
            className="w-12 h-12 rounded-full object-cover border flex-shrink-0"
          />
        ) : (
          <div className="w-12 h-12 rounded-full bg-blue-600 text-white flex items-center justify-center text-lg font-bold flex-shrink-0">
            {headerInitials}
          </div>
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm">{headerTitle}</span>
            <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${isOnline ? 'bg-green-500' : 'bg-gray-300'}`}
              title={isOnline ? 'Online' : 'Offline'} />
          </div>
          {headerSubtitle && (
            <div className="text-gray-500 text-xs">{headerSubtitle}</div>
          )}
          {statusMessage && (
            <div className="text-gray-600 text-xs mt-0.5">• {statusMessage}</div>
          )}
          {convData?.is_group && (
            <div className="text-gray-500 text-xs">{participantCount} participants</div>
          )}
        </div>
        <button onClick={fetchConversation} className="text-sm bg-gray-200 px-3 py-1 rounded hover:bg-gray-300 flex-shrink-0">
          Reload
        </button>
      </div>

      {/* Conversation debug info */}
      <div className="mb-4">
        {conversation.status && (
          <span className={`text-sm ${conversation.status < 300 ? 'text-green-600' : 'text-red-600'}`}>
            Status: {conversation.status}
          </span>
        )}
        {convData && (
          <div className="text-xs text-gray-400 mt-1">
            ID: {conversationId} | Encrypted: {String(convData.is_encrypted)}
          </div>
        )}
      </div>

      {/* Messages list */}
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-2">
          <h3 className="font-semibold text-sm">Messages</h3>
          <button onClick={fetchMessages} className="text-xs bg-gray-200 px-2 py-1 rounded hover:bg-gray-300">Refresh</button>
          {messages.status && (
            <span className={`text-xs ${messages.status < 300 ? 'text-green-600' : 'text-red-600'}`}>
              Status: {messages.status}
            </span>
          )}
        </div>
        {allMessages.length > 0 ? (
          <div className="bg-white border rounded p-3 max-h-64 overflow-auto space-y-2">
            {allMessages.map((m) => (
              <div key={m.id} className="text-sm border-b pb-2 last:border-0">
                <div className="flex justify-between text-xs text-gray-400">
                  <span>Sender: {m.sender_id}</span>
                  <span>{m.created_at}</span>
                </div>
                <div className="text-gray-800 mt-1">
                  <span className="text-xs bg-gray-100 px-1 rounded mr-1">{m.message_type}</span>
                  {m.content_encrypted}
                </div>
                {m.is_edited && <span className="text-xs text-orange-500"> (edited)</span>}
                {m.is_deleted && <span className="text-xs text-red-500"> (deleted)</span>}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400">No messages yet.</p>
        )}
      </div>

      {/* Send message form */}
      <div className="mb-4">
        <h3 className="font-semibold text-sm mb-2">Send Message</h3>
        <p className="text-xs text-gray-400 mb-2">POST /api/v1/messages/</p>
        <form onSubmit={handleSend} className="space-y-2 max-w-md">
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Message content (sent as content_encrypted)"
            className="w-full border rounded px-3 py-2 text-sm"
            rows={2}
            required
          />
          <input
            value={messageType}
            onChange={(e) => setMessageType(e.target.value)}
            placeholder="message_type (default: text)"
            className="w-full border rounded px-3 py-2 text-sm"
          />
          <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">Send</button>
          {sendResult.status && (
            <span className={`ml-3 text-sm ${sendResult.status < 300 ? 'text-green-600' : 'text-red-600'}`}>
              Status: {sendResult.status}
            </span>
          )}
        </form>
      </div>

      <DebugPanel request={sendResult.request} response={sendResult.response} error={sendResult.error} />
    </div>
  )
}