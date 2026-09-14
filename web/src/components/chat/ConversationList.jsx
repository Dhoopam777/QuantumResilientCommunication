import { useState, useEffect } from 'react'
import { conversationApi } from '../../lib/api'
import { useAuth } from '../../context/AuthContext'
import { useChat } from '../../context/ChatContext'
import { WebSocketClient } from '../../lib/websocket'
import ConversationCard from './ConversationCard'
import EmptyState from '../common/EmptyState'
import Spinner from '../common/Spinner'
import Button from '../common/Button'
import { Link } from 'react-router-dom'
import { ComposeIcon } from '../icons'

export default function ConversationList({ activeConversationId, search = '' }) {
  const { isLoggedIn, user } = useAuth()
  const [conversations, setConversations] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const { incrementUnread, resetUnread } = useChat()

  const fetchConversations = async () => {
    setLoading(true)
    setError(null)
    const res = await conversationApi.list()
    setLoading(false)
    if (res.status === 200 && Array.isArray(res.data)) {
      setConversations(res.data)
    } else {
      setError(res.error || 'Failed to load conversations')
    }
  }

  useEffect(() => {
    if (isLoggedIn) fetchConversations()
  }, [isLoggedIn])

  useEffect(() => {
    const refresh = () => fetchConversations()
    window.addEventListener('conversation-created', refresh)
    return () => window.removeEventListener('conversation-created', refresh)
  }, [isLoggedIn])

  // Listen for new messages and increment unread count for non-active conversations
  useEffect(() => {
    const ws = new WebSocketClient()
    ws.on('new_message', (data) => {
      const convId = data.conversation_id || data.id
      if (convId && activeConversationId !== convId) {
        incrementUnread(convId)
      }
    })
    return () => ws.disconnect()
  }, [activeConversationId, incrementUnread])

  // Filter by search
  const filtered = search
    ? conversations.filter((c) => {
        const title = c.is_group
          ? c.group_name || 'Group'
          : c.participants?.find((p) => p.user_id !== user?.id)?.display_name ||
            c.participants?.find((p) => p.user_id !== user?.id)?.username ||
            ''
        return title.toLowerCase().includes(search.toLowerCase())
      })
    : conversations

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="flex items-center justify-between px-4 pt-4 pb-2">
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted">
          Recent
          <span className="ml-1.5 inline-flex rounded-full bg-surface-hover px-1.5 py-0.5 text-[9px] font-semibold text-text-secondary normal-case tracking-normal">
            {filtered.length}
          </span>
        </h2>
        <Link
          to="/test/conversations/new"
          className="icon-btn"
          aria-label="Start a conversation"
          title="Start a conversation"
        >
          <ComposeIcon className="w-4 h-4" />
        </Link>
      </div>

      {loading && (
        <div className="flex justify-center py-8">
          <Spinner />
        </div>
      )}

      {error && (
        <div className="px-4 py-3 text-sm text-danger">{error}</div>
      )}

      {!loading && !error && filtered.length === 0 && (
        <EmptyState
          icon="💬"
          title={search ? 'No results' : 'No conversations yet'}
          description={search ? 'Try a different search term.' : 'Start a new conversation to begin chatting.'}
          action={!search && (
            <Link to="/test/conversations/new">
              <Button>New Conversation</Button>
            </Link>
          )}
        />
      )}

      {!loading && filtered.length > 0 && (
        <div className="px-2 pb-3 space-y-0.5">
          {filtered.map((c, index) => (
            <ConversationCard
              key={c.id}
              conversation={c}
              currentUserId={user?.id}
              isActive={c.id === activeConversationId}
              style={{ animationDelay: `${Math.min(index, 10) * 35}ms` }}
            />
          ))}
        </div>
      )}
    </div>
  )
}