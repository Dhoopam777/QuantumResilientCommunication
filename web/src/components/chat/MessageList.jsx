import { useEffect, useRef, useState, useCallback } from 'react'
import EmptyState from '../common/EmptyState'
import { ChatIcon } from '../icons'
import MessageBubble from './MessageBubble'
import MessageActionsHost from './MessageActionsHost'

function dayLabel(isoString) {
  if (!isoString) return ''
  const date = new Date(isoString)
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const target = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime()
  const diffDays = Math.round((today - target) / 86400000)
  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  return date.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })
}

function DateDivider({ label }) {
  if (!label) return null
  return (
    <div className="flex items-center justify-center py-3" aria-hidden="true">
      <span className="px-3 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider text-text-muted bg-surface-hover">
        {label}
      </span>
    </div>
  )
}

export default function MessageList({
  messages = [],
  currentUserId,
  sessionReady = false,
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
  // Single active contextual menu across ALL messages (reaction picker, "more"
  // menu and delete dialog share this one state, so only one can ever be open).
  const [menu, setMenu] = useState(null)

  // Close the open menu whenever the message list is replaced.
  useEffect(() => {
    console.log('[MessageList] messages identity changed -> closing menu')
    setMenu(null)
  }, [messages])

  // Close the open menu when edit mode begins for another message.
  useEffect(() => {
    if (editingId) setMenu(null)
  }, [editingId])

  const closeMenu = useCallback(() => setMenu(null), [])

  const handleOpenMore = useCallback((message, anchorEl, position) => {
    const anchorRect = anchorEl?.getBoundingClientRect?.() ?? null
    setMenu((current) =>
      current && current.message.id === message.id && current.kind === 'more'
        ? null
        : { message, kind: 'more', anchorEl, anchorRect, position },
    )
  }, [])

  const handleOpenReactions = useCallback((message, anchorEl, position) => {
    const anchorRect = anchorEl?.getBoundingClientRect?.() ?? null
    setMenu((current) =>
      current && current.message.id === message.id && current.kind === 'reaction'
        ? null
        : { message, kind: 'reaction', anchorEl, anchorRect, position },
    )
  }, [])

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
      <div className="flex-1 overflow-y-auto flex items-center justify-center">
        <EmptyState
          icon={<ChatIcon className="w-8 h-8" />}
          title="No messages yet"
          description="Say hello to start the conversation!"
        />
      </div>
    )
  }

  return (
    <>
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-1">
      {messages.map((m, index) => {
        const showDivider =
          index === 0 ||
          (m.created_at && messages[index - 1]?.created_at &&
            new Date(m.created_at).toDateString() !== new Date(messages[index - 1].created_at).toDateString())
        return (
          <div key={`div-${m.id}`}>
            {showDivider && <DateDivider label={dayLabel(m.created_at)} />}
            <div
              key={m.id}
              ref={(el) => { messageRefs.current[m.id] = el }}
              style={{ animationDelay: `${Math.min(index, 12) * 30}ms` }}
              className={`rounded-xl transition-colors duration-500 ${highlightedId === m.id ? 'bg-accent-soft ring-1 ring-accent/30' : ''
                }`}
            >
              <MessageBubble
                message={m}
                isOutgoing={m.sender_id === currentUserId}
                sessionReady={sessionReady}
                onReply={onReply}
                onScrollToMessage={handleScrollToMessage}
                onEdit={onEdit}
                onDelete={onDelete}
                isEditing={editingId === m.id}
                onStartEdit={onStartEdit}
                onCancelEdit={onCancelEdit}
                onReact={onReact}
                currentUserId={currentUserId}
                onOpenReactions={handleOpenReactions}
                onOpenMore={handleOpenMore}
                onCloseMenu={closeMenu}
              />
            </div>
          </div>
        )
      })}
      <div ref={bottomRef} />
      </div>
      <MessageActionsHost
        menu={menu}
        currentUserId={currentUserId}
        onClose={closeMenu}
        onDelete={onDelete}
        onReact={onReact}
      />
    </>
  )
}
