import { useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble'
import EmptyState from '../common/EmptyState'

export default function MessageList({ messages = [], currentUserId }) {
  const bottomRef = useRef(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length])

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
        <MessageBubble
          key={m.id}
          message={m}
          isOutgoing={m.sender_id === currentUserId}
        />
      ))}
      <div ref={bottomRef} />
    </div>
  )
}