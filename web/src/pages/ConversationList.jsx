import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { conversationApi, setLastConversationId } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import DebugPanel from '../components/DebugPanel'

/* ---- Helpers ---- */

function getInitials(name) {
  return (name || '?')
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

function relativeTime(isoString) {
  if (!isoString) return ''
  const date = new Date(isoString)
  const now = new Date()
  const diffMs = now - date
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h ago`
  const diffDay = Math.floor(diffHr / 24)
  if (diffDay < 7) return `${diffDay}d ago`
  return date.toLocaleDateString()
}

export default function ConversationList() {
  const { isLoggedIn, user } = useAuth()
  const [result, setResult] = useState({ response: null, error: null, status: null })

  const fetchConversations = async () => {
    setResult({ response: null, error: null, status: null })
    const res = await conversationApi.list()
    setResult({
      response: res.data,
      error: res.error || (res.status >= 400 ? JSON.stringify(res.data) : null),
      status: res.status,
    })
  }

  useEffect(() => {
    if (isLoggedIn) fetchConversations()
  }, [isLoggedIn])

  // Persist the selected conversation so it can be restored after refresh
  const handleConversationClick = (conversationId) => {
    setLastConversationId(conversationId)
  }

  if (!isLoggedIn) {
    return <p className="text-gray-500">Please log in first.</p>
  }

  const conversations = result.status === 200 && Array.isArray(result.response) ? result.response : []

  // For each conversation, determine the display title and the "other" participant (for 1:1)
  const getDisplayInfo = (c) => {
    if (c.is_group) {
      return {
        title: c.group_name || 'Group',
        subtitle: `${c.participants?.length || 0} participants`,
        otherParticipant: null,
      }
    }
    // For 1:1, find the other participant (not the current user)
    const other = c.participants?.find((p) => p.user_id !== user?.id)
    const name = other?.display_name || other?.username || 'Direct Message'
    return {
      title: name,
      subtitle: other ? `@${other.username}` : '',
      otherParticipant: other || null,
    }
  }

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">Conversation List</h2>
      <p className="text-sm text-gray-500 mb-4">GET /api/v1/conversations/</p>
      <button onClick={fetchConversations} className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 mb-4">
        Refresh
      </button>
      {result.status && (
        <span className={`ml-3 text-sm ${result.status < 300 ? 'text-green-600' : 'text-red-600'}`}>
          Status: {result.status}
        </span>
      )}
      {conversations.length > 0 && (
        <div className="space-y-2 mb-4">
          {conversations.map((c) => {
            const info = getDisplayInfo(c)
            const lastMsg = c.last_message
            const isOnline = info.otherParticipant?.is_online || false
            const avatarUrl = info.otherParticipant?.profile_picture_url
            const initials = getInitials(info.title)

            return (
              <Link
                key={c.id}
                to={`/test/conversations/${c.id}`}
                onClick={() => handleConversationClick(c.id)}
                className="block bg-white border rounded p-3 hover:bg-gray-50"
              >
                <div className="flex items-start gap-3">
                  {/* Avatar */}
                  {avatarUrl ? (
                    <img
                      src={avatarUrl}
                      alt={info.title}
                      className="w-10 h-10 rounded-full object-cover border flex-shrink-0"
                    />
                  ) : (
                    <div className="w-10 h-10 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-bold flex-shrink-0">
                      {initials}
                    </div>
                  )}

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="font-semibold text-sm truncate">{info.title}</span>
                        {isOnline && (
                          <span className="w-2 h-2 rounded-full bg-green-500 flex-shrink-0" title="Online" />
                        )}
                      </div>
                      <span className="text-gray-400 text-xs flex-shrink-0 ml-2">
                        {lastMsg ? relativeTime(lastMsg.created_at) : relativeTime(c.updated_at)}
                      </span>
                    </div>
                    {info.subtitle && (
                      <div className="text-gray-500 text-xs">{info.subtitle}</div>
                    )}
                    {lastMsg && (
                      <div className="text-gray-600 text-xs mt-1 truncate">
                        <span className="text-gray-400 mr-1">
                          {lastMsg.message_type !== 'text' ? `[${lastMsg.message_type}]` : ''}
                        </span>
                        {lastMsg.content_encrypted}
                      </div>
                    )}
                  </div>
                </div>
              </Link>
            )
          })}
        </div>
      )}
      {conversations.length === 0 && result.status === 200 && (
        <p className="text-sm text-gray-500 mb-4">No conversations found. <Link to="/test/conversations/new" className="underline">Create one</Link></p>
      )}
      <DebugPanel response={result.response} error={result.error} />
    </div>
  )
}