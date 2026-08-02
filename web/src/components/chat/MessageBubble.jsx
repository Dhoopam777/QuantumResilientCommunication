export default function MessageBubble({ message, isOutgoing }) {
  const time = message.created_at
    ? new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : ''

  return (
    <div className={`flex ${isOutgoing ? 'justify-end' : 'justify-start'} group relative`}>
      <div
        className={`relative max-w-[70%] rounded-bubble px-3 py-2 text-sm shadow-card ${
          isOutgoing
            ? 'bg-bubble-outgoing text-white rounded-br-sm'
            : 'bg-bubble-incoming text-text-primary rounded-bl-sm'
        }`}
      >
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

        {/* Future-ready: hover actions (reply, forward, delete, react) */}
        <div className="hidden group-hover:flex absolute -top-3 right-0 bg-surface-elevated border border-border rounded-lg shadow-popover px-1 py-0.5 gap-0.5">
          <button className="icon-btn !p-1 text-xs" title="React" aria-label="React">😀</button>
          <button className="icon-btn !p-1 text-xs" title="Reply" aria-label="Reply">↩️</button>
          <button className="icon-btn !p-1 text-xs" title="Forward" aria-label="Forward">➡️</button>
          <button className="icon-btn !p-1 text-xs" title="Delete" aria-label="Delete">🗑️</button>
        </div>
      </div>
    </div>
  )
}