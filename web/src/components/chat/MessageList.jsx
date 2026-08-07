import { useEffect, useRef, useState } from 'react'
import MessageBubble from './MessageBubble'
import EmptyState from '../common/EmptyState'

export default function MessageList({
  messages = [],
  currentUserId,
  onReply,
  onScrollToMessage,
  onEdit,
  onDelete,
  editingId,
  onStartEdit,
  onCancelEdit,
  onReact,
}) {
  const bottomRef = useRef(null)
  const messageRefs = useRef({})
  const [highlightedId, setHighlightedId] = useState(null)
  const highlightTimerRef = useRef(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length])

  // Clean up highlight timer on unmount
  useEffect(() => {
    return () => {
      if (highlightTimerRef.current) {
        clearTimeout(highlightTimerRef.current)
      }
    }
  }, [])

  const handleScrollToMessage = (messageId) => {
    const el = messageRefs.current[messageId]
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      setHighlightedId(messageId)
      if (highlightTimerRef.current) {
        clearTimeout(highlightTimerRef.current)
      }
      highlightTimerRef.current = setTimeout(() => setHighlightedId(null), 2000)
    }
  }

  if (messages.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto">
        <EmptyState
          icon="💬"
          title="No messages yet"
          description="Say hello to start the conversation!"
        />
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-2">
      {messages.map((m) => (
        <div
          key={m.id}
          ref={(el) => { messageRefs.current[m.id] = el }}
          className={`transition-colors duration-500 rounded-lg ${
            highlightedId === m.id ? 'bg-primary/10 ring-1 ring-primary/30' : ''
          }`}
        >
          <MessageBubble
            message={m}
            isOutgoing={m.sender_id === currentUserId}
            onReply={onReply}
            onScrollToMessage={handleScrollToMessage}
            onEdit={onEdit}
            onDelete={onDelete}
            isEditing={editingId === m.id}
            onStartEdit={onStartEdit}
            onCancelEdit={onCancelEdit}
            onReact={onReact}
            currentUserId={currentUserId}
          />
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
