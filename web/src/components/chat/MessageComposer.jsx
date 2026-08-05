import { useState } from 'react'
import IconButton from '../common/IconButton'

export default function MessageComposer({ onSend, disabled = false, replyTo = null, onCancelReply }) {
  const [content, setContent] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!content.trim() || disabled) return
    onSend(content, replyTo)
    setContent('')
  }

  return (
    <form onSubmit={handleSubmit} className="border-t border-border p-3 flex flex-col gap-2 flex-shrink-0">
      {/* Reply preview above composer */}
      {replyTo && (
        <div className="flex items-center gap-2 bg-surface-elevated border border-border rounded-lg px-3 py-2">
          <div className="flex-1 min-w-0">
            <div className="text-xs font-semibold text-primary truncate">
              {replyTo.is_deleted ? 'Deleted message' : `Replying to ${replyTo.sender_id ? 'message' : 'message'}`}
            </div>
            <div className="text-xs text-text-muted truncate">
              {replyTo.content_encrypted}
            </div>
          </div>
          <button
            type="button"
            onClick={onCancelReply}
            className="icon-btn !p-1 text-xs"
            title="Cancel reply"
            aria-label="Cancel reply"
          >
            ✕
          </button>
        </div>
      )}

      <div className="flex items-end gap-2">
        {/* Emoji button (placeholder) */}
        <IconButton label="Emoji" disabled title="Emoji picker coming soon">
          😀
        </IconButton>

        {/* Attachment button (placeholder) */}
        <IconButton label="Attach file" disabled title="File sharing coming soon">
          📎
        </IconButton>

        {/* Voice message button (placeholder) */}
        <IconButton label="Voice message" disabled title="Voice messages coming soon">
          🎤
        </IconButton>

        {/* Text input */}
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder={replyTo ? 'Reply...' : 'Type a message...'}
          className="input-base flex-1 resize-none"
          rows={1}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSubmit(e)
            }
          }}
          disabled={disabled}
          aria-label="Message"
        />

        {/* Send button */}
        <button
          type="submit"
          className="btn-primary !px-3 !py-2"
          disabled={!content.trim() || disabled}
          aria-label="Send message"
        >
          ➤
        </button>
      </div>
    </form>
  )
}