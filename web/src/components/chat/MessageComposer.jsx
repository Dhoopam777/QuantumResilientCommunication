import { useState } from 'react'
import IconButton from '../common/IconButton'

export default function MessageComposer({ onSend, disabled = false }) {
  const [content, setContent] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!content.trim() || disabled) return
    onSend(content)
    setContent('')
  }

  return (
    <form onSubmit={handleSubmit} className="border-t border-border p-3 flex items-end gap-2 flex-shrink-0">
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
        placeholder="Type a message..."
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
    </form>
  )
}