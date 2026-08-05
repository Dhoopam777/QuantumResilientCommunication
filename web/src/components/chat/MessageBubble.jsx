export default function MessageBubble({ message, isOutgoing, onReply, onScrollToMessage }) {
  const time = message.created_at
    ? new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : ''

  const handleReplyClick = () => {
    if (onReply) onReply(message)
  }

  const handleReplyPreviewClick = () => {
    if (onScrollToMessage && message.reply_preview) {
      onScrollToMessage(message.reply_preview.id)
    }
  }

  return (
    <div className={`flex ${isOutgoing ? 'justify-end' : 'justify-start'} group relative`}>
      <div
        className={`relative max-w-[70%] rounded-bubble px-3 py-2 text-sm shadow-card ${
          isOutgoing
            ? 'bg-bubble-outgoing text-white rounded-br-sm'
            : 'bg-bubble-incoming text-text-primary rounded-bl-sm'
        }`}
      >
        {/* Reply preview indicator */}
        {message.reply_preview && (
          <button
            onClick={handleReplyPreviewClick}
            className={`block w-full text-left mb-1.5 rounded-md px-2 py-1 text-xs border-l-2 ${
              isOutgoing
                ? 'bg-white/10 border-white/50 text-white/80 hover:bg-white/20'
                : 'bg-surface-elevated border-primary text-text-muted hover:bg-surface-hover'
            }`}
            title="Click to view original message"
          >
            <span className="font-semibold block truncate">
              {message.reply_preview.is_deleted ? 'Deleted message' : '↩️ Reply'}
            </span>
            <span className="block truncate opacity-80">
              {message.reply_preview.content_encrypted}
            </span>
          </button>
        )}

        {message.message_type !== 'text' && (
          <div className={`text-xs mb-1 ${isOutgoing ? 'text-white/80' : 'text-text-muted'}`}>
            [{message.message_type}]
          </div>
        )}
        <div className="break-words">{message.content_encrypted}</div>
        <div className={`flex items-center gap-1 mt-1 text-[10px] ${isOutgoing ? 'text-white/70' : 'text-text-muted'}`}>
          <span>{time}</span>
          {message.is_edited && <span>• edited</span>}
          {isOutgoing && <span>• ✓</span>}
        </div>

        {/* Hover actions: reply, forward, delete, react */}
        <div className="hidden group-hover:flex absolute -top-3 right-0 bg-surface-elevated border border-border rounded-lg shadow-popover px-1 py-0.5 gap-0.5">
          <button className="icon-btn !p-1 text-xs" title="React" aria-label="React">😀</button>
          <button
            className="icon-btn !p-1 text-xs"
            title="Reply"
            aria-label="Reply"
            onClick={handleReplyClick}
          >
            ↩️
          </button>
          <button className="icon-btn !p-1 text-xs" title="Forward" aria-label="Forward">➡️</button>
          <button className="icon-btn !p-1 text-xs" title="Delete" aria-label="Delete">🗑️</button>
        </div>
      </div>
    </div>
  )
}