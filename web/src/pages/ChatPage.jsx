import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate, useLocation, Link } from 'react-router-dom'
import {
  conversationApi,
  messageApi,
  getAccessToken,
  getLastConversationId,
  setLastConversationId,
} from '../lib/api'
import { WebSocketClient } from '../lib/websocket'
import { useAuth } from '../context/AuthContext'
import ChatLayout from '../components/chat/ChatLayout'
import ConversationList from '../components/chat/ConversationList'
import ChatHeader from '../components/chat/ChatHeader'
import MessageList from '../components/chat/MessageList'
import MessageComposer from '../components/chat/MessageComposer'
import DetailsPanel from '../components/chat/DetailsPanel'
import EmptyState from '../components/common/EmptyState'

export default function ChatPage() {
  const { conversationId } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const { isLoggedIn, user, accessToken, logout, registerWebSocket, unregisterWebSocket } = useAuth()
  const [conversation, setConversation] = useState(null)
  const [messages, setMessages] = useState([])
  const [wsStatus, setWsStatus] = useState('disconnected')
  const [wsMessages, setWsMessages] = useState([])
  const [search, setSearch] = useState('')
  const [replyTo, setReplyTo] = useState(null)
  const wsClientRef = useRef(null)
  const seenMessageIdsRef = useRef(new Set())
  const wsTokenRef = useRef('')

  const fetchConversation = useCallback(async () => {
    if (!conversationId) return
    const res = await conversationApi.get(conversationId)
    if (res.status === 200) {
      setConversation(res.data)
    }
  }, [conversationId])

  const fetchMessages = useCallback(async () => {
    if (!conversationId) return
    const res = await messageApi.list(conversationId)
    if (res.status === 200 && Array.isArray(res.data)) {
      setMessages(res.data)
      res.data.forEach((m) => {
        if (m.id) seenMessageIdsRef.current.add(m.id)
      })
    }
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
        navigate(`/test/chat/${lastId}`, { replace: true })
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
    registerWebSocket(wsClient)

    wsClient.on('new_message', (data) => {
      const msg = data.message
      if (!msg || !msg.id) return
      if (!seenMessageIdsRef.current.has(msg.id)) {
        seenMessageIdsRef.current.add(msg.id)
        setWsMessages((prev) => [...prev, msg])
      }
    })

    wsClient.on('auth_success', () => {
      setWsStatus('connected')
      wsClient.joinConversation(conversationId)
    })

    wsClient.on('auth_error', () => {
      setWsStatus('auth_failed')
    })

    wsClient.on('connection_close', () => {
      setWsStatus('disconnected')
    })

    wsClient.on('connection_open', () => {
      setWsStatus('connecting')
    })

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

  const handleReply = (message) => {
    setReplyTo(message)
  }

  const handleCancelReply = () => {
    setReplyTo(null)
  }

  const handleSend = async (content, replyTarget = null) => {
    if (!conversationId || !content.trim()) return
    const payload = {
      conversation_id: conversationId,
      content_encrypted: content,
      content_hash: btoa(content).slice(0, 32),
      message_type: 'text',
      reply_to: replyTarget ? replyTarget.id : null,
      reply_to_message_id: replyTarget ? replyTarget.id : null,
    }
    const res = await messageApi.send(payload)
    if (res.status === 201) {
      // WebSocket broadcast is the single source of truth for new messages
      setReplyTo(null)
    }
  }

  if (!isLoggedIn) {
    return <p className="text-gray-500">Please log in first.</p>
  }

  // Merge REST-fetched messages with WebSocket-received messages
  const allMessages = (() => {
    const restIds = new Set(messages.map((m) => m.id))
    const wsOnly = wsMessages.filter((m) => !restIds.has(m.id))
    return [...messages, ...wsOnly]
  })()

  const showDetails = location.pathname.endsWith('/details')

  return (
    <ChatLayout
      user={user}
      onLogout={logout}
      search={search}
      onSearchChange={setSearch}
      sidebarContent={
        <ConversationList activeConversationId={conversationId} search={search} />
      }
      showDetails={showDetails}
      detailsPanel={
        <DetailsPanel conversation={conversation} currentUserId={user?.id} />
      }
    >
      {conversationId ? (
        <>
          <ChatHeader conversation={conversation} currentUserId={user?.id} />
          <MessageList
            messages={allMessages}
            currentUserId={user?.id}
            onReply={handleReply}
          />
          <MessageComposer
            onSend={handleSend}
            disabled={!conversation}
            replyTo={replyTo}
            onCancelReply={handleCancelReply}
          />
        </>
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center">
          <EmptyState
            icon="💬"
            title="Welcome to QRC Chat"
            description="Select a conversation from the sidebar to start chatting, or create a new one."
          />
          <Link to="/test/conversations/new" className="btn-primary mt-2">
            New Conversation
          </Link>
        </div>
      )}
    </ChatLayout>
  )
}