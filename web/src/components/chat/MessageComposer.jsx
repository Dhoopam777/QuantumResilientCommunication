import { useState } from 'react'
import IconButton from '../common/IconButton'

export default function MessageComposer({ onSend, disabled = false, replyTo = null, onCancelReply }) {
  const [content, setContent] = useState('')
  const [files, setFiles] = useState([])
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if ((!content.trim() && files.length === 0) || disabled) return
    setError('')
    try {
      await onSend(content, replyTo, files)
      setContent('')
      setFiles([])
    } catch (sendError) {
      setError(sendError instanceof Error ? sendError.message : 'Unable to send message')
    }
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

        <label className="icon-btn cursor-pointer" title="Attach encrypted image">
          <span aria-hidden="true">📎</span>
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            multiple
            className="hidden"
            disabled={disabled}
            onChange={(event) => setFiles(Array.from(event.target.files || []))}
          />
        </label>

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
          disabled={(!content.trim() && files.length === 0) || disabled}
          aria-label="Send message"
        >
          ➤
        </button>
      </div>
      {files.length > 0 && (
        <div className="text-xs text-text-muted truncate">
          {files.map((file) => file.name).join(', ')}
        </div>
      )}
      {error && <div className="text-xs text-danger" role="alert">{error}</div>}
    </form>
  )
}