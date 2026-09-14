import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import {
  clearLastConversationId,
  getLastConversationId,
  setLastConversationId,
} from '../lib/api'

/**
 * Chat selection state shared across the app.
 *
 * The selected conversation ID is intentionally kept OUT of the browser URL:
 * clients never navigate to /test/chat/<uuid>. The real conversation ID still
 * exists here (and in localStorage for refresh resilience) so API calls,
 * WebSocket joins and secure sessions continue to use the true ID.
 */
const ChatContext = createContext(null)

export function ChatProvider({ children }) {
  const [activeConversationId, setActiveConversationId] = useState(() => getLastConversationId() || null)
  const [showDetails, setShowDetails] = useState(false)
  // Per-conversation unread message counts. Keyed by conversation ID.
  // When a new_message event arrives for a conversation that is not the
  // active one, its count is incremented. Selecting a conversation resets it.
  const [unreadCounts, setUnreadCounts] = useState({})

  const selectConversation = useCallback((conversationId) => {
    setActiveConversationId(conversationId || null)
    if (conversationId) setLastConversationId(conversationId)
    else clearLastConversationId()
    setShowDetails(false)
    // Reset unread count when conversation is selected
    setUnreadCounts((prev) => ({ ...prev, [conversationId]: 0 }))
  }, [])

  const openDetails = useCallback(() => setShowDetails(true), [])
  const closeDetails = useCallback(() => setShowDetails(false), [])

  const incrementUnread = useCallback((conversationId) => {
    setUnreadCounts((prev) => ({
      ...prev,
      [conversationId]: (prev[conversationId] || 0) + 1,
    }))
  }, [])

  const resetUnread = useCallback((conversationId) => {
    setUnreadCounts((prev) => ({ ...prev, [conversationId]: 0 }))
  }, [])

  const value = useMemo(
    () => ({
      activeConversationId,
      selectConversation,
      showDetails,
      openDetails,
      closeDetails,
      unreadCounts,
      incrementUnread,
      resetUnread,
    }),
    [activeConversationId, selectConversation, showDetails, openDetails, closeDetails, unreadCounts],
  )

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>
}

export function useChat() {
  const context = useContext(ChatContext)
  if (!context) throw new Error('useChat must be used within ChatProvider')
  return context
}